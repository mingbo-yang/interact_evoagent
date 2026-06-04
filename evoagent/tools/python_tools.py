"""Python execution tool — run Python code via sandbox or directly."""

from pathlib import Path

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.sandbox.base import BaseSandbox
from evoagent.tools.base import BaseTool, RiskLevel, resolve_workspace_path
from evoagent.tools.schema import ToolResult


class PythonInput(BaseModel):
    code: str | None = Field(default=None, description="Python code to execute (mutually exclusive with script_path).")
    script_path: str | None = Field(default=None, description="Path to a Python script to execute.")
    timeout: int = Field(default=30, description="Timeout in seconds.")


class PythonTool(BaseTool):
    name = "python"
    description = "Execute Python code or a Python script via the sandbox."
    input_schema = PythonInput
    risk_level = RiskLevel.HIGH

    def __init__(self, workspace: Path, sandbox: BaseSandbox | None = None):
        self.workspace = workspace
        self.sandbox = sandbox

    async def run(self, code: str | None = None, script_path: str | None = None,
                  timeout: int = 30) -> ToolResult:
        if not code and not script_path:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error="Either 'code' or 'script_path' must be provided.",
            )

        if self.sandbox:
            result = await self.sandbox.run_python(code=code, script_path=script_path, timeout=timeout)
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            return ToolResult(
                call_id=generate_id("call"), name=self.name,
                success=result.success,
                output=output.strip() or "(no output)",
                error=None if result.success else f"Exit code: {result.exit_code}",
                metadata={"exit_code": result.exit_code},
            )

        # Fallback without sandbox
        import subprocess
        import tempfile

        if script_path:
            resolved = resolve_workspace_path(script_path, self.workspace, must_exist=True)
            proc = subprocess.run(
                ["python3", str(resolved)], capture_output=True, text=True,
                timeout=timeout, cwd=str(self.workspace),
            )
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir=str(self.workspace)
            ) as f:
                f.write(code)
                tmp_path = f.name
            try:
                proc = subprocess.run(
                    ["python3", tmp_path], capture_output=True, text=True,
                    timeout=timeout, cwd=str(self.workspace),
                )
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        output = proc.stdout
        if proc.stderr:
            output += "\n[stderr]\n" + proc.stderr
        return ToolResult(
            call_id=generate_id("call"), name=self.name,
            success=proc.returncode == 0,
            output=output.strip() or "(no output)",
            error=None if proc.returncode == 0 else f"Exit code: {proc.returncode}",
            metadata={"exit_code": proc.returncode},
        )
