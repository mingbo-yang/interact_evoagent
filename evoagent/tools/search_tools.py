"""Search tool — pure Python grep text search within the workspace."""

import fnmatch
import re
from pathlib import Path

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.tools.base import BaseTool, RiskLevel, resolve_workspace_path
from evoagent.tools.schema import ToolResult

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class GrepInput(BaseModel):
    pattern: str = Field(..., description="Pattern or regex to search for.")
    path: str = Field(default=".", description="Directory to search in.")
    glob: str | None = Field(default=None, description="File pattern filter, e.g. '*.py'.")
    max_results: int = Field(default=100, description="Maximum matching lines to return.")


class GrepTool(BaseTool):
    name = "grep"
    description = "Search for a pattern in files within the workspace using Python regex."
    input_schema = GrepInput
    risk_level = RiskLevel.LOW

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self, pattern: str, path: str = ".", glob: str | None = None,
                  max_results: int = 100) -> ToolResult:
        try:
            resolved = resolve_workspace_path(path, self.workspace, must_exist=True)
            compiled = re.compile(pattern)
            matches: list[str] = []
            count = 0
            truncated = False

            for fp in sorted(resolved.rglob("*")):
                # Skip hidden dirs
                if any(part in _SKIP_DIRS for part in fp.parts):
                    continue
                if not fp.is_file():
                    continue
                if glob and not fnmatch.fnmatch(fp.name, glob):
                    continue
                if fp.stat().st_size > _MAX_FILE_SIZE:
                    continue
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if compiled.search(line):
                        rel = fp.relative_to(resolved)
                        matches.append(f"{rel}:{i}: {line[:200]}")
                        count += 1
                        if count >= max_results:
                            truncated = True
                            break
                if truncated:
                    break

            if not matches:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=True,
                    output="No matches found.",
                    metadata={"pattern": pattern, "matches": 0},
                )
            output = "\n".join(matches)
            if truncated:
                output += f"\n... (truncated at {max_results} matches; refine the pattern for more)"
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=output, metadata={"pattern": pattern, "matches": count},
            )
        except re.error as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error=f"Invalid regex pattern: {e}",
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )
