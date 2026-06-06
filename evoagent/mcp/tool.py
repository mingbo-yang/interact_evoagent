"""MCPTool — wrap an MCP server tool as an EvoAgent BaseTool."""

import time
from typing import Any

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso
from evoagent.mcp.client import MCPClient
from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.schema import ToolResult

_MAX_OUTPUT = 30_000


def _extract_text(result: dict[str, Any]) -> str:
    """Flatten an MCP tool result's content blocks into text."""
    content = result.get("content")
    if isinstance(content, list):
        parts = [
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        joined = "\n".join(p for p in parts if p)
        if joined:
            return joined
    import json
    return json.dumps(result, ensure_ascii=False)


class MCPTool(BaseTool):
    """Adapter exposing one MCP server tool through the BaseTool interface.

    Validation is delegated to the MCP server (the model-facing JSON schema is
    the server-provided ``inputSchema``), so :meth:`arun` is overridden to send
    arguments straight to the server rather than coercing them through a local
    Pydantic model.
    """

    risk_level = RiskLevel.MEDIUM

    def __init__(
        self,
        client: MCPClient,
        mcp_name: str,
        description: str = "",
        schema: dict[str, Any] | None = None,
        name_prefix: str = "",
    ):
        self._client = client
        self._mcp_name = mcp_name
        self.name = f"{name_prefix}{mcp_name}" if name_prefix else mcp_name
        self.description = description or f"MCP tool '{mcp_name}'."
        self._schema = schema or {"type": "object", "properties": {}}

    def to_openai_tool_schema(self) -> dict[str, Any]:
        params = dict(self._schema)
        params.pop("title", None)
        params.pop("$schema", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        return await self._call(kwargs)

    async def arun(self, arguments: dict[str, Any]) -> ToolResult:
        return await self._call(arguments or {})

    async def _call(self, arguments: dict[str, Any]) -> ToolResult:
        started = utc_now_iso()
        t0 = time.monotonic()
        try:
            result = await self._client.call_tool(self._mcp_name, arguments)
            text = _extract_text(result)[:_MAX_OUTPUT]
            ok = not bool(result.get("isError"))
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=ok,
                output=text if ok else "", error=None if ok else text,
                metadata={"mcp_tool": self._mcp_name},
                started_at=started, finished_at=utc_now_iso(),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as e:
            return ToolResult(
                call_id=generate_id("call"), name=self.name, success=False,
                error=f"MCP call failed: {e}", started_at=started,
                finished_at=utc_now_iso(),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )


async def register_mcp_tools(
    registry: Any, client: MCPClient, name_prefix: str = "mcp__"
) -> list[str]:
    """Start the client, discover its tools, and register them.

    Returns the list of registered (prefixed) tool names. Tools whose names
    collide with already-registered tools are skipped.
    """
    if client._proc is None:
        await client.start()
    tools = await client.list_tools()
    registered: list[str] = []
    for t in tools:
        name = t.get("name")
        if not name:
            continue
        tool = MCPTool(
            client, name, t.get("description", ""),
            t.get("inputSchema") or t.get("input_schema"), name_prefix,
        )
        if tool.name in registry:
            continue
        registry.register(tool)
        registered.append(tool.name)
    return registered
