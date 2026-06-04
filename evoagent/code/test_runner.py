"""CodeTestRunner — execute tests and capture results."""

import subprocess
import time
from pathlib import Path

from pydantic import BaseModel


class TestResult(BaseModel):
    success: bool = False
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    command: str = ""


class CodeTestRunner:
    """Run tests in the workspace and capture results.

    Defaults to pytest, but accepts any test command.
    Renamed from TestRunner to avoid pytest collection warning.
    """

    __test__ = False

    def __init__(self, workspace: str | Path, default_command: str = "python -m pytest -q"):
        self.workspace = Path(workspace).resolve()
        self.default_command = default_command

    def run(self, command: str | None = None, timeout: int = 60) -> TestResult:
        cmd = command or self.default_command
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=str(self.workspace),
            )
            return TestResult(
                success=proc.returncode == 0, exit_code=proc.returncode,
                stdout=proc.stdout, stderr=proc.stderr,
                duration_ms=int((time.monotonic() - t0) * 1000), command=cmd,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False, exit_code=-1,
                stderr=f"Test timed out after {timeout}s",
                duration_ms=timeout * 1000, command=cmd,
            )
