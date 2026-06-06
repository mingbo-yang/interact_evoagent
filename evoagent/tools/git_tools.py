"""Git tools — status and diff."""

import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.schema import ToolResult


class GitStatusInput(BaseModel):
    """No arguments needed for git status."""


class GitDiffInput(BaseModel):
    path: str | None = Field(default=None, description="Optional: limit diff to a specific path.")


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Show the working tree status (git status --short)."
    input_schema = GitStatusInput
    risk_level = RiskLevel.LOW

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self) -> ToolResult:
        try:
            proc = subprocess.run(
                ["git", "status", "--short"], capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=10, cwd=str(self.workspace),
            )
            output = proc.stdout.strip() or "(clean — no changes)"
            if proc.returncode != 0:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=proc.stderr.strip() or "Not a git repository.",
                    output=output,
                    metadata={"exit_code": proc.returncode},
                )
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=output,
                metadata={"exit_code": 0},
            )
        except FileNotFoundError:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error="git is not installed or not found in PATH.",
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Show changes in the working tree (git diff)."
    input_schema = GitDiffInput
    risk_level = RiskLevel.LOW

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self, path: str | None = None) -> ToolResult:
        try:
            cmd = ["git", "diff"]
            if path:
                cmd.append(path)
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=10, cwd=str(self.workspace),
            )
            output = proc.stdout.strip() or "(no changes)"
            if proc.returncode != 0:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=proc.stderr.strip() or "Not a git repository.",
                    output=output,
                    metadata={"exit_code": proc.returncode},
                )
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=output,
                metadata={"exit_code": 0, "chars": len(output)},
            )
        except FileNotFoundError:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error="git is not installed or not found in PATH.",
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )
