"""MCP (Model Context Protocol) client integration.

Provides a minimal stdio JSON-RPC client that can connect to an MCP server
subprocess, discover its tools, and expose them as EvoAgent tools.
"""

from evoagent.mcp.client import MCPClient, MCPError
from evoagent.mcp.tool import MCPTool, register_mcp_tools

__all__ = ["MCPClient", "MCPError", "MCPTool", "register_mcp_tools"]
