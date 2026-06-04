"""CodeAgent — a specialized agent for software engineering tasks.

Supports LLM-powered patch generation with structured PatchPlan,
enhanced rule-based fallback for common bug patterns, and
iterative test-fix loop.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evoagent.code.diagnostics import Diagnostics
from evoagent.code.patch import PatchManager
from evoagent.code.repo_map import RepoMap
from evoagent.code.schema import FileEdit
from evoagent.code.search import CodeSearch
from evoagent.code.test_runner import CodeTestRunner, TestResult


@dataclass
class CodeAgentResult:
    success: bool = False
    task: str = ""
    changed_files: list[str] = field(default_factory=list)
    summary: str = ""
    tests_run: int = 0
    test_result: TestResult | None = None
    diff: str = ""
    remaining_risks: list[str] = field(default_factory=list)
    iterations: int = 0
    errors: list[str] = field(default_factory=list)


class CodeAgent:
    def __init__(self, workspace: str | Path, model_router: Any = None,
                 test_command: str = "python -m pytest -q", max_iterations: int = 5):
        self.workspace = Path(workspace).resolve()
        self.model_router = model_router
        self.max_iterations = max_iterations
        self.repo_map = RepoMap()
        self.search = CodeSearch(self.workspace)
        self.patch = PatchManager(self.workspace)
        self.runner = CodeTestRunner(self.workspace, default_command=test_command)
        self.diagnostics = Diagnostics()

    async def run(self, task: str) -> CodeAgentResult:
        errors: list[str] = []
        summary = self.repo_map.summarize(self.workspace)
        likely_files: list[str] = []

        if self.model_router:
            try:
                likely_files = await self._llm_locate(task, summary)
            except Exception as e:
                errors.append(f"LLM locate failed: {e}")

        test_result: TestResult | None = None
        iteration = 0
        previous_failures: list[str] = []

        for iteration in range(1, self.max_iterations + 1):
            if self.model_router:
                try:
                    diag = Diagnostics.parse_structured(
                        (test_result.stdout + test_result.stderr) if test_result else "")
                    await self._llm_patch(task, likely_files, diag, previous_failures)
                except Exception as e:
                    errors.append(f"LLM patch failed: {e}")
            else:
                self._rule_based_analyze(test_result, task) if test_result else None

            test_result = self.runner.run()
            if test_result.success:
                break
            prev_out = test_result.stdout + test_result.stderr
            previous_failures.append(prev_out[-1000:])
            errors.append(f"Iteration {iteration}: tests failed")

        diff = self.patch.get_diff()
        return CodeAgentResult(
            success=test_result is not None and test_result.success,
            task=task, changed_files=self.patch.changed_files(),
            summary=f"Fixed bug: {task}" if self.patch.changed_files() else "No changes made.",
            tests_run=iteration, test_result=test_result, diff=diff,
            iterations=iteration, errors=errors,
        )

    def _rule_based_analyze(self, test_result: TestResult | None, task: str) -> None:
        if not test_result:
            return
        output = test_result.stdout + test_result.stderr
        files = Diagnostics.identify_likely_files(output)
        if not files:
            return
        target = files[0]
        p = self.workspace / target
        if not p.exists():
            return
        content = p.read_text(encoding="utf-8")
        low = output.lower()

        if "zerodivisionerror" in low or "division by zero" in low:
            for pattern in ["return a / b", "return x / y", "return val /"]:
                if pattern in content and "/ 0" not in content:
                    self.patch.edit_file(target, pattern,
                                         f"return 0 if {pattern.split('/')[1].strip()} == 0 else {pattern.replace('return ', '')}")
                    return
        if "off-by-one" in low or ("assert" in low and ("+ 1" in output or "- 1" in output)):
            pass  # LLM needed
        if "importerror" in low or "modulenotfounderror" in low:
            match = __import__("re").search(r"No module named '(\w+)'", output)
            if match:
                mod = match.group(1)
                self.patch.edit_file(target, f"import {mod}", f"# TODO: install {mod} or add to requirements\nimport {mod}")
                return
        if "filenotfounderror" in low:
            match = __import__("re").search(r"No such file.*: '(\S+)'", output)
            if match:
                missing = match.group(1)
                if "open(" in content:
                    self.patch.edit_file(target, f"open(\"{missing}\"", f"open(\"{Path(missing).name}\"")
                    return

    async def _llm_locate(self, task: str, repo_summary: str) -> list[str]:
        provider = self.model_router._get_provider("default")
        import json

        from evoagent.code.prompts import REPO_ANALYSIS_PROMPT
        from evoagent.models.schema import LLMRequest
        prompt = REPO_ANALYSIS_PROMPT.format(repo_summary=repo_summary, task=task)
        resp = await provider.chat(LLMRequest(messages=[{"role": "user", "content": prompt}]))
        try:
            return json.loads(resp.content).get("likely_files", [])
        except json.JSONDecodeError:
            return []

    async def _llm_patch(self, task: str, files: list[str], diagnostics: dict,
                         previous_failures: list[str]) -> None:
        provider = self.model_router._get_provider("executor")
        import json

        from evoagent.code.prompts import PATCH_PLANNING_PROMPT
        from evoagent.models.schema import LLMRequest

        file_contents = ""
        for f in files[:5]:
            p = self.workspace / f
            if p.exists():
                file_contents += f"\n=== {f} ===\n{p.read_text()[:2000]}\n"

        prompt = PATCH_PLANNING_PROMPT.format(
            task=task, files="\n".join(files), file_contents=file_contents,
            diagnostics=json.dumps(diagnostics),
            previous_failures="\n".join(previous_failures[-2:]),
        )
        resp = await provider.chat(LLMRequest(messages=[{"role": "user", "content": prompt}]))
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            return
        for edit_data in data.get("files_to_edit", []):
            edit = FileEdit(**edit_data)
            self.patch.edit_file(edit.path, edit.old_text, edit.new_text)
