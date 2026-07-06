from __future__ import annotations

from app.schemas.tool_result import ToolResult


class CodexTool:
    """Adapter placeholder for Codex as external code tool."""

    async def run(self, task: str, repo_path: str, sandbox_mode: str = "workspace-write") -> ToolResult:
        return ToolResult(
            success=False,
            summary="CodexTool adapter scaffolded but not yet connected to runtime credentials.",
            logs=[f"task={task}", f"repo_path={repo_path}", f"sandbox_mode={sandbox_mode}"],
            error="NOT_IMPLEMENTED",
        )

