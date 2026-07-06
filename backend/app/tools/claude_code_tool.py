from __future__ import annotations

from app.schemas.tool_result import ToolResult


class ClaudeCodeTool:
    """Adapter placeholder for Claude Code as external code tool."""

    async def run(self, task: str, repo_path: str, allowed_tools: list[str]) -> ToolResult:
        return ToolResult(
            success=False,
            summary="ClaudeCodeTool adapter scaffolded but not yet connected to runtime credentials.",
            logs=[f"task={task}", f"repo_path={repo_path}", f"allowed_tools={allowed_tools}"],
            error="NOT_IMPLEMENTED",
        )

