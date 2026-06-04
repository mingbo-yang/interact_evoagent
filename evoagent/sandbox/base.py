"""BaseSandbox — abstract interface for sandbox execution environments."""

from abc import ABC, abstractmethod

from evoagent.sandbox.schema import SandboxResult
from evoagent.sandbox.workspace import Workspace


class BaseSandbox(ABC):
    """Abstract sandbox for executing commands and code safely.

    All shell, Python, and file operations should go through
    a sandbox to enforce workspace boundaries and permissions.
    """

    def __init__(self, workspace: Workspace | None = None):
        self.workspace = workspace or Workspace()

    @abstractmethod
    async def run_shell(
        self, command: str, cwd: str | None = None, timeout: int = 30
    ) -> SandboxResult:
        """Execute a shell command within the sandbox.

        Args:
            command: Shell command to run.
            cwd: Working directory (must be inside workspace).
            timeout: Timeout in seconds.

        Returns:
            SandboxResult with stdout, stderr, exit_code.
        """
        ...

    @abstractmethod
    async def run_python(
        self, code: str | None = None, script_path: str | None = None, timeout: int = 30
    ) -> SandboxResult:
        """Execute Python code within the sandbox.

        Args:
            code: Python code string to execute.
            script_path: Path to a Python script (inside workspace).
            timeout: Timeout in seconds.

        Returns:
            SandboxResult.
        """
        ...

    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read a file inside the workspace.

        Args:
            path: Relative path within workspace.

        Returns:
            File contents as string.
        """
        ...

    @abstractmethod
    async def write_file(self, path: str, content: str, overwrite: bool = False) -> None:
        """Write a file inside the workspace.

        Args:
            path: Relative path within workspace.
            content: Content to write.
            overwrite: Whether to overwrite existing files.
        """
        ...
