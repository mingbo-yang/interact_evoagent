"""LocalSandbox — execute commands locally with permission checks."""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

from evoagent.sandbox.base import BaseSandbox
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.sandbox.schema import PermissionDecision, SandboxResult
from evoagent.sandbox.workspace import Workspace


class LocalSandbox(BaseSandbox):
    """Sandbox that executes commands locally on the host machine.

    Enforces:
    - Workspace boundaries (no file access outside workspace)
    - Permission policy checks on all operations
    - Timeout on shell/python execution
    """

    def __init__(
        self,
        workspace: Workspace | None = None,
        policy: PermissionPolicy | None = None,
        auto_approve: bool = False,
    ):
        super().__init__(workspace)
        self.policy = policy or PermissionPolicy()
        # When False (default), operations requiring approval (ASK) are
        # refused. Trusted internal callers (e.g. the eval harness running a
        # configured test_command) may set this True.
        self.auto_approve = auto_approve

    # ── Shell ─────────────────────────────────────────────────────────

    async def run_shell(
        self, command: str, cwd: str | None = None, timeout: int = 30
    ) -> SandboxResult:
        # Permission check
        decision = self.policy.check("shell", command, risk_level="high")
        if decision == PermissionDecision.DENY:
            return SandboxResult(
                success=False, stderr=f"Permission denied: {command}",
                command=command, exit_code=-1,
            )
        if decision == PermissionDecision.ASK and not self.auto_approve:
            return SandboxResult(
                success=False,
                stderr=f"Permission required (not auto-approved): {command}",
                command=command, exit_code=-1,
            )

        work_dir = str(self.workspace.root)
        if cwd:
            resolved = self.workspace.resolve_path(cwd)
            work_dir = str(resolved)

        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, cwd=work_dir,
            )
            return SandboxResult(
                success=proc.returncode == 0,
                stdout=proc.stdout, stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=int((time.monotonic() - t0) * 1000),
                command=command, cwd=work_dir,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False, stderr=f"Timeout ({timeout}s)",
                command=command, exit_code=-1,
                duration_ms=timeout * 1000,
            )

    # ── Python ────────────────────────────────────────────────────────

    async def run_python(
        self, code: str | None = None, script_path: str | None = None, timeout: int = 30
    ) -> SandboxResult:
        decision = self.policy.check("python", code or script_path or "", risk_level="high")
        if decision == PermissionDecision.DENY:
            return SandboxResult(
                success=False, stderr="Permission denied: python execution",
                exit_code=-1,
            )
        if decision == PermissionDecision.ASK and not self.auto_approve:
            return SandboxResult(
                success=False, stderr="Permission required (not auto-approved): python execution",
                exit_code=-1,
            )

        t0 = time.monotonic()
        try:
            if script_path:
                resolved = self.workspace.resolve_path(script_path)
                proc = subprocess.run(
                    [sys.executable, str(resolved)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    timeout=timeout, cwd=str(self.workspace.root),
                )
            else:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, dir=str(self.workspace.root),
                    encoding="utf-8",
                ) as f:
                    f.write(code or "")
                    tmp_path = f.name
                try:
                    proc = subprocess.run(
                        [sys.executable, tmp_path], capture_output=True, text=True,
                        encoding="utf-8", errors="replace",
                        timeout=timeout, cwd=str(self.workspace.root),
                    )
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=proc.stdout, stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False, stderr=f"Python timeout ({timeout}s)", exit_code=-1,
            )

    # ── File I/O ──────────────────────────────────────────────────────

    async def read_file(self, path: str) -> str:
        resolved = self.workspace.resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        return resolved.read_text(encoding="utf-8")

    async def write_file(self, path: str, content: str, overwrite: bool = False) -> None:
        resolved = self.workspace.resolve_path(path)
        if resolved.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {resolved}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
