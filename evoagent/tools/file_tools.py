"""File tools — read, write, edit, and list directory contents."""

from pathlib import Path

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.tools.base import (
    _DEFAULT_HIDDEN_DIRS,
    BaseTool,
    RiskLevel,
    resolve_workspace_path,
)
from evoagent.tools.schema import ToolResult

# ── Input schemas ─────────────────────────────────────────────────────


class ReadFileInput(BaseModel):
    path: str = Field(..., description="File path relative to workspace.")
    start_line: int | None = Field(default=None, description="First line to read (1-indexed).")
    end_line: int | None = Field(default=None, description="Last line to read (1-indexed).")
    max_chars: int = Field(default=50000, description="Maximum characters to return.")


class WriteFileInput(BaseModel):
    path: str = Field(..., description="File path relative to workspace.")
    content: str = Field(..., description="Content to write.")
    overwrite: bool = Field(default=False, description="Whether to overwrite an existing file.")


class EditFileInput(BaseModel):
    path: str = Field(..., description="File path relative to workspace.")
    old_text: str = Field(..., description="Exact text to find and replace.")
    new_text: str = Field(..., description="Text to substitute in place of old_text.")
    replace_all: bool = Field(default=False, description="Replace all occurrences.")


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="Directory path relative to workspace.")
    recursive: bool = Field(default=False, description="Whether to list recursively.")
    max_entries: int = Field(default=200, description="Maximum entries to return.")


# ── Tools ─────────────────────────────────────────────────────────────


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read a file from the workspace. Supports line ranges and character limits."
    input_schema = ReadFileInput
    risk_level = RiskLevel.LOW

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self, path: str, start_line: int | None = None,
                  end_line: int | None = None, max_chars: int = 50000) -> ToolResult:
        resolved = resolve_workspace_path(path, self.workspace, must_exist=True)
        if resolved.is_dir():
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error=f"Path is a directory, not a file: {resolved}",
            )
        try:
            content = resolved.read_text(encoding="utf-8")
            if start_line is not None or end_line is not None:
                lines = content.split("\n")
                s = (start_line or 1) - 1
                e = end_line or len(lines)
                content = "\n".join(lines[s:e])
            if len(content) > max_chars:
                content = content[:max_chars] + "\n... (truncated)"
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=content,
                metadata={"path": str(resolved), "chars": len(content)},
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file in the workspace. Creates parent directories automatically."
    input_schema = WriteFileInput
    risk_level = RiskLevel.MEDIUM

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self, path: str, content: str, overwrite: bool = False) -> ToolResult:
        try:
            resolved = resolve_workspace_path(path, self.workspace)
            if resolved.exists() and not overwrite:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=f"File already exists: {resolved}. Use overwrite=true to replace.",
                )
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=f"Written {len(content)} chars to {resolved}",
                metadata={"path": str(resolved), "chars": len(content)},
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Find and replace text in a file. By default, old_text must be unique in the file."
    input_schema = EditFileInput
    risk_level = RiskLevel.MEDIUM

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self, path: str, old_text: str, new_text: str,
                  replace_all: bool = False) -> ToolResult:
        try:
            resolved = resolve_workspace_path(path, self.workspace, must_exist=True)
            content = resolved.read_text(encoding="utf-8")
            count = content.count(old_text)
            if count == 0:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=f"old_text not found in {resolved}",
                )
            if not replace_all and count > 1:
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=f"old_text found {count} times in {resolved}. "
                          "Use replace_all=true or make old_text unique.",
                )
            new_content = content.replace(old_text, new_text)
            resolved.write_text(new_content, encoding="utf-8")
            replacements = count if replace_all else 1
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=f"Replaced {replacements} occurrence(s) in {resolved}",
                metadata={"path": str(resolved), "replacements": replacements},
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )


class ListDirTool(BaseTool):
    name = "list_directory"
    description = "List files and directories in a workspace directory. Hidden dirs (.git, __pycache__, etc.) are excluded by default."
    input_schema = ListDirInput
    risk_level = RiskLevel.LOW

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def run(self, path: str = ".", recursive: bool = False,
                  max_entries: int = 200) -> ToolResult:
        try:
            resolved = resolve_workspace_path(path, self.workspace, must_exist=True)
            if not resolved.is_dir():
                return ToolResult(
                    call_id=generate_id("call"), name=self.name, success=False,
                    error=f"Not a directory: {resolved}",
                )
            entries: list[str] = []
            if recursive:
                for p in sorted(resolved.rglob("*")):
                    if any(part in _DEFAULT_HIDDEN_DIRS for part in p.parts):
                        continue
                    rel = p.relative_to(resolved)
                    suffix = "/" if p.is_dir() else ""
                    entries.append(f"{rel}{suffix}")
            else:
                for p in sorted(resolved.iterdir()):
                    if p.name in _DEFAULT_HIDDEN_DIRS:
                        continue
                    suffix = "/" if p.is_dir() else ""
                    entries.append(f"{p.name}{suffix}")

            if len(entries) > max_entries:
                total = len(entries)
                entries = entries[:max_entries]
                entries.append(f"... ({total} total, showing first {max_entries})")

            output = "\n".join(entries) if entries else "(empty directory)"
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=True,
                output=output, metadata={"path": str(resolved), "count": len(entries)},
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False, error=str(e),
            )
