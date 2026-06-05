"""ToolRegistry — register, discover, and execute tools."""

from pathlib import Path
from typing import Any

from evoagent.core.errors import ToolError
from evoagent.tools.base import BaseTool
from evoagent.tools.schema import ToolResult


class ToolRegistry:
    """Central registry for all tools.

    Tools are registered by name and can be looked up,
    listed, and executed. The registry also generates
    OpenAI-compatible function-calling schemas for all
    registered tools.

    Usage:
        registry = ToolRegistry()
        registry.register(MyTool())
        schemas = registry.get_tool_schemas()
        result = await registry.run_tool("my_tool", {"arg": "val"})
    """

    def __init__(self, workspace: Path | None = None):
        """Initialize the registry.

        Args:
            workspace: Optional workspace root for tool path resolution.
        """
        self._tools: dict[str, BaseTool] = {}
        self.workspace = workspace or Path.cwd()

    # ── CRUD ──────────────────────────────────────────────────────────

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Args:
            tool: The tool to register.

        Raises:
            ToolError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ToolError(
                f"Tool '{tool.name}' is already registered. "
                "Unregister it first or use a different name."
            )
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry.

        Args:
            name: Tool name to remove.

        Raises:
            ToolError: If the tool is not registered.
        """
        if name not in self._tools:
            raise ToolError(f"Tool '{name}' is not registered.")
        del self._tools[name]

    def get(self, name: str) -> BaseTool:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            The BaseTool instance.

        Raises:
            ToolError: If the tool is not registered.
        """
        if name not in self._tools:
            raise ToolError(f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """Return the names of all registered tools."""
        return sorted(self._tools.keys())

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible function-calling schemas for all tools.

        Returns:
            List of schema dicts suitable for LLM tool_choice.
        """
        return [tool.to_openai_tool_schema() for tool in self._tools.values()]

    # ── Execution ─────────────────────────────────────────────────────

    async def run_tool(self, name: str, arguments: dict[str, Any],
                        call_id: str | None = None) -> ToolResult:
        """Look up and execute a tool by name.

        Args:
            name: Tool name.
            arguments: Raw argument dict.
            call_id: Optional ToolCall.id to preserve in ToolResult.

        Returns:
            ToolResult with call_id matching the triggering ToolCall.id.

        Raises:
            ToolError: If the tool is not registered.
        """
        tool = self.get(name)
        result = await tool.arun(arguments)
        if call_id:
            result.call_id = call_id
        return result

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
