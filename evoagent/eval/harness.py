"""EvalHarness — run evaluation tasks against an agent."""

import time
from pathlib import Path
from typing import Any

from evoagent.core.ids import generate_id
from evoagent.eval.checkers import evaluate_check_async
from evoagent.eval.task import EvalResult, EvalTask
from evoagent.sandbox.base import BaseSandbox
from evoagent.sandbox.local import LocalSandbox
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.sandbox.workspace import Workspace


class EvalHarness:
    """Runs EvalTasks against an Agent and collects results.

    test_command checks go through Sandbox with PermissionPolicy
    for security. Contains/regex/exact checks do not need sandbox.

    Usage:
        harness = EvalHarness(agent, trace_dir=".runs/eval")
        results = await harness.run_suite(tasks)
    """

    def __init__(self, agent: Any, trace_dir: str = ".runs/eval",
                 sandbox: BaseSandbox | None = None):
        self.agent = agent
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox = sandbox or LocalSandbox(
            workspace=Workspace("."),
            policy=PermissionPolicy(),
            auto_approve=True,
        )

    async def run_task(self, task: EvalTask) -> EvalResult:
        """Run a single evaluation task.

        Args:
            task: The EvalTask to run.

        Returns:
            EvalResult with success, score, metrics.
        """
        run_id = generate_id("eval_run")
        t0 = time.monotonic()

        # Setup workspace files if specified
        workspace = task.workspace or "."
        for fname, content in task.input_files.items():
            fp = Path(workspace) / fname
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")

        try:
            result = await self.agent.run(task.instruction)
            output = result.final_answer if hasattr(result, "final_answer") else str(result)
        except Exception as e:
            return EvalResult(
                task_id=task.task_id, run_id=run_id, success=False,
                error=str(e), started_at="", finished_at="",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        duration_ms = int((time.monotonic() - t0) * 1000)

        # Evaluate. test_command checks must run in the task's workspace, so
        # use a sandbox rooted there rather than the harness default.
        success = False
        if task.expected_check:
            success = await evaluate_check_async(output, task.expected_check, workspace, sandbox=self.sandbox)
        elif task.test_command:
            check_sandbox = self._sandbox_for(workspace)
            success = await evaluate_check_async(
                "", f'{{"type": "test_command", "command": "{task.test_command}"}}',
                workspace, sandbox=check_sandbox,
            )
        elif task.expected_output:
            success = task.expected_output in output

        metrics = {
            "steps": getattr(result, "steps_taken", 0),
            "tool_calls": getattr(result, "tool_calls", 0),
            "duration_ms": duration_ms,
        }

        return EvalResult(
            task_id=task.task_id, run_id=run_id,
            success=success, score=1.0 if success else 0.0,
            metrics=metrics,
            started_at="", finished_at="",
            duration_ms=duration_ms,
            cost_usd=getattr(result, "total_cost", 0.0),
            error=result.error if hasattr(result, "error") and result.error else None,
        )

    def _sandbox_for(self, workspace: str) -> BaseSandbox:
        """Return a sandbox rooted at ``workspace`` for trusted test_command
        execution. Reuses the harness sandbox when it already matches."""
        existing_root = getattr(getattr(self.sandbox, "workspace", None), "root", None)
        if existing_root is not None and str(existing_root) == str(Path(workspace).resolve()):
            return self.sandbox
        return LocalSandbox(
            workspace=Workspace(workspace),
            policy=getattr(self.sandbox, "policy", None) or PermissionPolicy(),
            auto_approve=True,
        )

    async def run_suite(self, tasks: list[EvalTask]) -> list[EvalResult]:
        """Run a suite of tasks and return all results.

        Args:
            tasks: List of EvalTask objects.

        Returns:
            List of EvalResult objects.
        """
        results: list[EvalResult] = []
        for task in tasks:
            try:
                result = await self.run_task(task)
            except Exception as e:
                result = EvalResult(task_id=task.task_id, run_id="error", success=False, error=str(e))
            results.append(result)
        return results
