"""Tests for parallel read-only tool execution and deterministic ordering."""

import asyncio

import pytest

from evoagent.core.message import MessageRole
from evoagent.core.react import READ_ONLY_TOOLS, ReActEngine, ReActRunResult
from evoagent.sandbox.schema import PermissionDecision
from evoagent.tools.schema import ToolResult


class _Call:
    def __init__(self, cid, name, arguments=None):
        self.id = cid
        self.name = name
        self.arguments = arguments or {}


class _AllowPolicy:
    def check(self, *a, **k):
        return PermissionDecision.ALLOW


class _DenyReadPolicy:
    def check(self, action_type, target, risk_level="low"):
        if action_type == "file_read":
            return PermissionDecision.DENY
        return PermissionDecision.ALLOW


class _FakeRegistry:
    """Records concurrency and execution order; read tools block on a barrier."""

    def __init__(self, concurrency_probe=None):
        self.order = []
        self.active = 0
        self.max_active = 0
        self._probe = concurrency_probe

    async def run_tool(self, name, arguments, call_id=None):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self._probe is not None and name in READ_ONLY_TOOLS:
                # Yield so peers in the same gather batch can ramp up.
                await asyncio.sleep(0.02)
            self.order.append(name)
            return ToolResult(call_id=call_id, name=name, success=True, output=f"out:{name}")
        finally:
            self.active -= 1


def _engine(registry, policy=None):
    return ReActEngine(
        model_router=object(),
        tool_registry=registry,
        permission_policy=policy or _AllowPolicy(),
    )


@pytest.mark.asyncio
async def test_messages_in_original_order():
    reg = _FakeRegistry()
    engine = _engine(reg)
    calls = [
        _Call("a", "read_file", {"path": "x"}),
        _Call("b", "write_file", {"path": "y"}),
        _Call("c", "list_directory", {"path": "z"}),
    ]
    result = ReActRunResult()
    msgs = await engine._run_tool_calls(calls, result)
    assert [m.tool_call_id for m in msgs] == ["a", "b", "c"]
    assert all(m.role == MessageRole.TOOL for m in msgs)
    assert [t.call_id for t in result.tool_results] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_consecutive_read_only_run_concurrently():
    reg = _FakeRegistry(concurrency_probe=True)
    engine = _engine(reg)
    calls = [
        _Call("a", "read_file", {"path": "1"}),
        _Call("b", "grep", {"pattern": "x"}),
        _Call("c", "list_todos", {}),
    ]
    result = ReActRunResult()
    msgs = await engine._run_tool_calls(calls, result)
    assert [m.tool_call_id for m in msgs] == ["a", "b", "c"]
    # All three are read-only and consecutive → executed in one gather batch.
    assert reg.max_active >= 2


@pytest.mark.asyncio
async def test_write_between_reads_not_concurrent_across_boundary():
    reg = _FakeRegistry(concurrency_probe=True)
    engine = _engine(reg)
    calls = [
        _Call("a", "read_file", {"path": "1"}),
        _Call("b", "write_file", {"path": "2"}),
        _Call("c", "read_file", {"path": "3"}),
    ]
    result = ReActRunResult()
    await engine._run_tool_calls(calls, result)
    # The write must run strictly between the two reads.
    assert reg.order.index("write_file") == 1
    assert reg.order[0] == "read_file"
    assert reg.order[2] == "read_file"


@pytest.mark.asyncio
async def test_denied_call_still_yields_message_in_order():
    reg = _FakeRegistry()
    engine = _engine(reg, policy=_DenyReadPolicy())
    calls = [
        _Call("a", "read_file", {"path": "x"}),  # denied
        _Call("b", "write_file", {"path": "y"}),  # allowed
    ]
    result = ReActRunResult()
    msgs = await engine._run_tool_calls(calls, result)
    assert [m.tool_call_id for m in msgs] == ["a", "b"]
    assert "Permission denied" in msgs[0].content
    assert "out:write_file" in msgs[1].content
    # Denied read never reached the registry.
    assert "read_file" not in reg.order


@pytest.mark.asyncio
async def test_tool_timeout_produces_error_message():
    class _SlowRegistry:
        async def run_tool(self, name, arguments, call_id=None):
            await asyncio.sleep(1.0)
            return ToolResult(call_id=call_id, name=name, success=True, output="late")

    engine = ReActEngine(
        model_router=object(),
        tool_registry=_SlowRegistry(),
        permission_policy=_AllowPolicy(),
        tool_timeout=0.05,
    )
    calls = [_Call("a", "read_file", {"path": "x"})]
    result = ReActRunResult()
    msgs = await engine._run_tool_calls(calls, result)
    assert "timed out" in msgs[0].content
    assert result.tool_results[0].success is False
