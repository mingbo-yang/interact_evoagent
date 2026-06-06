"""DockerSandbox — execute commands in a Docker container via docker CLI."""

import shutil
import subprocess
import time

from evoagent.sandbox.base import BaseSandbox
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.sandbox.schema import SandboxResult
from evoagent.sandbox.workspace import Workspace


class DockerSandbox(BaseSandbox):
    """Sandbox that executes commands inside a Docker container.

    Uses docker CLI (no docker Python SDK dependency).
    Falls back to clear error if docker is not installed.

    Configuration:
        image: python:3.11-slim
        network_disabled: true
        timeout: 60
        mount_mode: rw (or ro)
        memory_limit: optional
        cpu_limit: optional
    """

    def __init__(
        self,
        workspace: Workspace | None = None,
        policy: PermissionPolicy | None = None,
        image: str = "python:3.11-slim",
        network_disabled: bool = True,
        timeout: int = 60,
        mount_mode: str = "rw",
        memory_limit: str | None = None,
        cpu_limit: str | None = None,
        user: str | None = None,
        auto_approve: bool = False,
    ):
        super().__init__(workspace)
        self.policy = policy or PermissionPolicy()
        self.image = image
        self.network_disabled = network_disabled
        self.timeout = timeout
        self.mount_mode = mount_mode
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.user = user
        self.auto_approve = auto_approve

    async def run_shell(self, command: str, cwd: str | None = None, timeout: int = 30) -> SandboxResult:
        decision = self.policy.check("shell", command, risk_level="high")
        if decision.value == "deny":
            return SandboxResult(success=False, stderr="Permission denied.", command=command, exit_code=-1)
        if decision.value == "ask" and not self.auto_approve:
            return SandboxResult(success=False, stderr=f"Permission required (not auto-approved): {command}",
                                 command=command, exit_code=-1)
        return self._docker_exec(command, timeout=timeout, cwd=cwd)

    async def run_python(self, code: str | None = None, script_path: str | None = None,
                         timeout: int = 30) -> SandboxResult:
        decision = self.policy.check("python", code or script_path or "", risk_level="high")
        if decision.value == "deny":
            return SandboxResult(success=False, stderr="Permission denied.", exit_code=-1)
        if decision.value == "ask" and not self.auto_approve:
            return SandboxResult(success=False, stderr="Permission required (not auto-approved): python execution",
                                 exit_code=-1)
        if script_path:
            cmd = f"python /workspace/{script_path}"
        else:
            escaped = (code or "").replace("'", "'\\''")
            cmd = f"python -c '{escaped}'"
        return self._docker_exec(cmd, timeout=timeout)

    async def read_file(self, path: str) -> str:
        resolved = self.workspace.resolve_path(path)
        return resolved.read_text(encoding="utf-8")

    async def write_file(self, path: str, content: str, overwrite: bool = False) -> None:
        resolved = self.workspace.resolve_path(path)
        if resolved.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {resolved}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

    def _docker_exec(self, command: str, timeout: int = 30, cwd: str | None = None) -> SandboxResult:
        if shutil.which("docker") is None:
            return SandboxResult(success=False, stderr="docker CLI not found. Install Docker to use DockerSandbox.",
                                 command=command, exit_code=-1)
        ws = str(self.workspace.root.resolve())
        mount_flag = f"{ws}:/workspace:{self.mount_mode},Z"
        full_cmd = f"cd /workspace && {command}"
        # Correct order: docker run [opts] [mounts] [network] [resources] IMAGE sh -c COMMAND
        cmd = ["docker", "run", "--rm", "-v", mount_flag]
        if self.network_disabled:
            cmd.extend(["--network", "none"])
        if self.memory_limit:
            cmd.extend(["--memory", self.memory_limit])
        if self.cpu_limit:
            cmd.extend(["--cpus", self.cpu_limit])
        if self.user:
            cmd.extend(["-u", self.user])
        cmd.append(self.image)
        cmd.extend(["sh", "-c", full_cmd])

        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout)
            return SandboxResult(
                success=proc.returncode == 0, stdout=proc.stdout, stderr=proc.stderr,
                exit_code=proc.returncode, duration_ms=int((time.monotonic() - t0) * 1000),
                command=command,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(success=False, stderr=f"Timeout ({timeout}s)", command=command,
                                 exit_code=-1, duration_ms=timeout * 1000)
