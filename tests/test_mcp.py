"""Tests for P1.4 MCP client — real stdio JSON-RPC against a local echo server."""

import sys
from pathlib import Path

import pytest

from evoagent.mcp.client import MCPClient, MCPError
from evoagent.mcp.tool import MCPTool, register_mcp_tools
from evoagent.tools.registry import ToolRegistry

_SERVER = str(Path(__file__).parent / "_mcp_echo_server.py")


def _client():
    return MCPClient([sys.executable, _SERVER])


@pytest.mark.asyncio
async def test_initialize_and_list_tools():
    client = _client()
    async with client:
        assert client.server_info.get("serverInfo", {}).get("name") == "echo-server"
        tools = await client.list_tools()
        names = {t["name"] for t in tools}
        assert names == {"echo", "add"}


@pytest.mark.asyncio
async def test_call_echo():
    async with _client() as client:
        result = await client.call_tool("echo", {"text": "hello mcp"})
        assert result["isError"] is False
        assert result["content"][0]["text"] == "hello mcp"


@pytest.mark.asyncio
async def test_call_add():
    async with _client() as client:
        result = await client.call_tool("add", {"a": 2, "b": 40})
        assert result["content"][0]["text"] == "42"


@pytest.mark.asyncio
async def test_unknown_tool_is_error():
    async with _client() as client:
        result = await client.call_tool("nope", {})
        assert result["isError"] is True


@pytest.mark.asyncio
async def test_register_mcp_tools_into_registry():
    registry = ToolRegistry(workspace=Path("."))
    client = _client()
    try:
        names = await register_mcp_tools(registry, client)
        assert "mcp__echo" in names
        assert "mcp__add" in names
        # The wrapped tool runs through the registry like any other tool.
        res = await registry.run_tool("mcp__echo", {"text": "via registry"}, call_id="x")
        assert res.success
        assert res.output == "via registry"
        assert res.call_id == "x"
        # add through the registry
        res2 = await registry.run_tool("mcp__add", {"a": 5, "b": 6})
        assert res2.output == "11"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_mcp_tool_exposes_server_schema():
    async with _client() as client:
        tools = await client.list_tools()
        schema = {t["name"]: t for t in tools}
        tool = MCPTool(client, "echo", schema["echo"]["description"],
                       schema["echo"]["inputSchema"], name_prefix="mcp__")
        oai = tool.to_openai_tool_schema()
        assert oai["function"]["name"] == "mcp__echo"
        assert "text" in oai["function"]["parameters"]["properties"]
        # isError result surfaces as a failed ToolResult.
        res = await tool.arun({"text": "x"})
        assert res.success


@pytest.mark.asyncio
async def test_request_before_start_raises():
    client = _client()
    with pytest.raises(MCPError):
        await client.list_tools()
