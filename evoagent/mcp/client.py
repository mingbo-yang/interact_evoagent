"""MCPClient — a minimal stdio JSON-RPC 2.0 client for MCP servers.

Speaks the MCP stdio transport: newline-delimited JSON-RPC messages over a
subprocess's stdin/stdout. Supports the initialize handshake, ``tools/list``,
and ``tools/call``. Requests are serialized with a lock so concurrent tool
calls cannot interleave reads.
"""

import asyncio
import json
import os
from typing import Any

_PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    """Raised on MCP transport or JSON-RPC errors."""


class MCPClient:
    """Connects to an MCP server over stdio and issues JSON-RPC requests."""

    def __init__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout: float = 30.0,
    ):
        if not command:
            raise ValueError("command must be a non-empty list (program + args).")
        self.command = command
        self.env = env
        self.cwd = cwd
        self.timeout = timeout
        self._proc: asyncio.subprocess.Process | None = None
        self._id = 0
        self._lock = asyncio.Lock()
        self.server_info: dict[str, Any] = {}

    async def start(self) -> None:
        """Spawn the server and perform the initialize handshake."""
        full_env = {**os.environ, **(self.env or {})}
        self._proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
            cwd=self.cwd,
        )
        result = await self._request(
            "initialize",
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "evoagent", "version": "1.0"},
            },
        )
        self.server_info = result or {}
        await self._notify("notifications/initialized")

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the server's advertised tools."""
        result = await self._request("tools/list", {})
        return (result or {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a tool by name; returns the raw MCP result object."""
        result = await self._request(
            "tools/call", {"name": name, "arguments": arguments or {}}
        )
        return result or {}

    async def close(self) -> None:
        """Terminate the server subprocess."""
        if self._proc is None:
            return
        try:
            if self._proc.stdin and not self._proc.stdin.is_closing():
                self._proc.stdin.close()
        except Exception:
            pass
        try:
            self._proc.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5)
        except (TimeoutError, Exception):
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None

    async def __aenter__(self) -> "MCPClient":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ── Internal JSON-RPC ─────────────────────────────────────────────
    async def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise MCPError("MCP client is not started.")
        async with self._lock:
            self._id += 1
            req_id = self._id
            payload = {"jsonrpc": "2.0", "id": req_id, "method": method,
                       "params": params or {}}
            self._proc.stdin.write((json.dumps(payload) + "\n").encode())
            await self._proc.stdin.drain()
            while True:
                try:
                    raw = await asyncio.wait_for(
                        self._proc.stdout.readline(), timeout=self.timeout
                    )
                except TimeoutError as e:
                    raise MCPError(f"Timed out waiting for response to '{method}'.") from e
                if not raw:
                    raise MCPError("MCP server closed the connection.")
                try:
                    data = json.loads(raw.decode().strip())
                except json.JSONDecodeError:
                    continue  # skip non-JSON log lines
                # Ignore notifications and responses to other ids.
                if data.get("id") != req_id:
                    continue
                if "error" in data:
                    raise MCPError(f"MCP error for '{method}': {data['error']}")
                return data.get("result")

    async def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise MCPError("MCP client is not started.")
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self._proc.stdin.write((json.dumps(payload) + "\n").encode())
        await self._proc.stdin.drain()
