"""Shell tool — execute bash commands via sandbox with unified PermissionPolicy."""

import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.sandbox.base import BaseSandbox
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.tools.base import BaseTool, RiskLevel, resolve_workspace_path
from evoagent.tools.schema import ToolResult


class BashInput(BaseModel):
    command: str = Field(..., description="The shell command to execute.")
    timeout: int = Field(default=30, description="Timeout in seconds.")
    cwd: str | None = Field(default=None, description="Working directory for the command.")


class BashTool(BaseTool):
    name = "bash"
    description = "Execute a shell command. All commands go through PermissionPolicy."
    input_schema = BashInput
    risk_level = RiskLevel.HIGH

    def __init__(self, workspace: Path, sandbox: BaseSandbox | None = None,
                 policy: PermissionPolicy | None = None, auto_approve: bool = False):
        self.workspace = workspace
        self.sandbox = sandbox
        self.policy = policy or PermissionPolicy()
        # When False (default), commands requiring approval (ASK) are refused
        # rather than silently executed. Trusted callers that have already
        # obtained approval may set this True.
        self.auto_approve = auto_approve

    async def run(self, command: str, timeout: int = 30, cwd: str | None = None) -> ToolResult:
        # Always check via PermissionPolicy
        decision = self.policy.check("shell", command, risk_level="high")
        if decision.value == "deny":
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error="Permission denied: command blocked by policy.",
                metadata={"command": command, "decision": "deny"},
            )
        if decision.value == "ask" and not self.auto_approve:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error="Permission required: this command needs approval and was "
                      "not auto-approved in this context.",
                metadata={"command": command, "decision": "ask"},
            )

        # Use sandbox if available
        if self.sandbox:
            result = await self.sandbox.run_shell(command, cwd=cwd, timeout=timeout)
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            return ToolResult(
                call_id=generate_id("call"), name=self.name,
                success=result.success,
                output=output.strip() or "(no output)",
                error=None if result.success else f"Exit code: {result.exit_code}",
                metadata={"exit_code": result.exit_code, "command": command,
                          "cwd": cwd or str(self.workspace)},
            )

        # Direct execution, bounded to the workspace.
        work_dir = str(self.workspace)
        if cwd:
            try:
                work_dir = str(resolve_workspace_path(cwd, self.workspace, must_exist=True))
            except (PermissionError, FileNotFoundError) as e:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=str(e), metadata={"command": command},
                )
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, cwd=work_dir,
            )
            output = proc.stdout
            if proc.stderr:
                output += "\n[stderr]\n" + proc.stderr
            return ToolResult(
                call_id=generate_id("call"), name=self.name,
                success=proc.returncode == 0,
                output=output.strip() or "(no output)",
                error=None if proc.returncode == 0 else f"Exit code: {proc.returncode}",
                metadata={"exit_code": proc.returncode, "command": command,
                          "cwd": work_dir},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error=f"Command timed out ({timeout}s).",
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )
