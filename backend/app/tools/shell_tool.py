from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


RISKY_TOKENS = (
    "rm -rf",
    "del /f",
    "format",
    "shutdown",
    "reboot",
    "pip install",
    "npm install",
)


@dataclass
class ShellResult:
    success: bool
    output: str
    error: str | None = None
    requires_approval: bool = False


class ShellTool:
    """First stable external tool for MVP."""

    def __init__(self, workspace: str):
        self.workspace = workspace

    def _needs_approval(self, command: str) -> bool:
        cmd = command.lower()
        return any(t in cmd for t in RISKY_TOKENS)

    async def run(self, command: str) -> ShellResult:
        if self._needs_approval(command):
            return ShellResult(
                success=False,
                output="",
                error="Dangerous command requires user approval.",
                requires_approval=True,
            )
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            output = (proc.stdout or "").strip()
            if proc.stderr:
                output = (output + "\n" + proc.stderr).strip()
            return ShellResult(
                success=proc.returncode == 0,
                output=output or "(no output)",
                error=None if proc.returncode == 0 else f"Exit code: {proc.returncode}",
            )
        except Exception as e:
            return ShellResult(success=False, output="", error=str(e))

    def default_listing_command(self) -> str:
        return "dir" if os.name == "nt" else "ls -la"

