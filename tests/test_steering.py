"""Tests for P1.2 interrupt/steering control of the ReAct loop."""

import asyncio

import pytest

from evoagent.core.message import Message, MessageRole, ToolCall
from evoagent.core.react import ReActEngine
from evoagent.core.steering import SteeringController
from evoagent.models.base import BaseLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.models.schema import LLMResponse
from evoagent.tools.builtin import create_builtin_registry
from evoagent.tools.schema import ToolResult


class ScriptedProvider(BaseLLMProvider):
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.seen_messages = []

    @property
    def provider_name(self) -> str:
        return "scripted"

    async def chat(self, request):
        self.calls += 1
        self.seen_messages.append(list(request.messages))
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(content="done", model="m", finish_reason="stop")

    async def structured_chat(self, request, schema):  # pragma: no cover
        raise NotImplementedError

    async def stream_chat(self, request):  # pragma: no cover
        yield "done"


def _router(provider):
    return ModelRouter(providers={"executor": provider, "default": provider})


class _SchemaRegistry:
    """Minimal registry with a controllable run_tool."""

    def __init__(self, run_tool):
        self._run_tool = run_tool

    def get_tool_schemas(self):
        return []

    async def run_tool(self, name, arguments, call_id=None):
        return await self._run_tool(name, arguments, call_id)


@pytest.mark.asyncio
async def test_inject_adds_user_message_before_model_call():
    provider = ScriptedProvider([
        LLMResponse(content="final", model="m", finish_reason="stop"),
    ])
    steering = SteeringController()
    steering.inject("please also check the logs")

    async def _run_tool(name, arguments, call_id=None):  # pragma: no cover
        return ToolResult(call_id=call_id, name=name, success=True, output="x")

    engine = ReActEngine(_router(provider), _SchemaRegistry(_run_tool),
                         steering=steering, enable_compaction=False)
    messages = [Message(role=MessageRole.USER, content="go")]
    result = await engine.run_turn(messages)
    assert result.stop_reason == "final"
    # The injected steering text is present as a user message and was sent.
    assert any(m.role == MessageRole.USER and "check the logs" in m.content
               for m in messages)
    assert any("check the logs" in m.content
               for m in provider.seen_messages[0])


@pytest.mark.asyncio
async def test_request_stop_after_tool_round():
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="t1", name="noop", arguments={}),
        ]),
        LLMResponse(content="should not reach", model="m", finish_reason="stop"),
    ])
    steering = SteeringController()

    async def _run_tool(name, arguments, call_id=None):
        # Mid-round, the user asks to stop after this tool completes.
        steering.request_stop()
        return ToolResult(call_id=call_id, name=name, success=True, output="ran")

    engine = ReActEngine(_router(provider), _SchemaRegistry(_run_tool),
                         steering=steering, enable_compaction=False,
                         ask_fallback="allow")
    messages = [Message(role=MessageRole.USER, content="do one then stop")]
    result = await engine.run_turn(messages)
    assert result.stop_reason == "interrupted"
    # Only one model call happened; the loop stopped before the second.
    assert provider.calls == 1
    # The tool still ran and produced a tool message.
    assert any(m.role == MessageRole.TOOL and m.content == "ran" for m in messages)


@pytest.mark.asyncio
async def test_cancel_interrupts_long_tool():
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="slow", name="sleep_tool", arguments={}),
        ]),
        LLMResponse(content="unreached", model="m", finish_reason="stop"),
    ])
    steering = SteeringController()
    started = asyncio.Event()

    async def _run_tool(name, arguments, call_id=None):
        started.set()
        await asyncio.sleep(30)  # long-running; should be cancelled
        return ToolResult(call_id=call_id, name=name, success=True, output="late")

    engine = ReActEngine(_router(provider), _SchemaRegistry(_run_tool),
                         steering=steering, enable_compaction=False,
                         ask_fallback="allow")
    messages = [Message(role=MessageRole.USER, content="run long task")]
    task = asyncio.create_task(engine.run_turn(messages))
    await asyncio.wait_for(started.wait(), timeout=5)
    steering.cancel()
    result = await asyncio.wait_for(task, timeout=5)
    assert result.stop_reason == "interrupted"
    tool_msg = next(m for m in messages if m.role == MessageRole.TOOL)
    assert "cancelled" in tool_msg.content.lower()
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_forbid_file_denies_write(tmp_path):
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="w", name="write_file",
                     arguments={"path": "secret.py", "content": "x = 1"}),
        ]),
        LLMResponse(content="blocked", model="m", finish_reason="stop"),
    ])
    steering = SteeringController()
    steering.forbid_file("secret.py")
    registry = create_builtin_registry(tmp_path)
    engine = ReActEngine(_router(provider), registry, ask_fallback="allow",
                         steering=steering, enable_compaction=False)
    messages = [Message(role=MessageRole.USER, content="write the file")]
    result = await engine.run_turn(messages)
    tool_msg = next(m for m in messages if m.role == MessageRole.TOOL)
    assert "forbade" in tool_msg.content.lower()
    assert not (tmp_path / "secret.py").exists()
    assert any("forbade" in e.lower() for e in result.errors)
    assert result.final_text == "blocked"


def test_forbid_file_matching():
    s = SteeringController()
    s.forbid_file("config.py")
    assert s.is_forbidden("config.py")
    assert s.is_forbidden("src/config.py")
    assert s.is_forbidden("/abs/path/config.py")
    assert not s.is_forbidden("other.py")
    assert not s.is_forbidden("")


def test_drain_injections_clears():
    s = SteeringController()
    s.inject("a")
    s.inject("  ")  # ignored (blank)
    s.inject("b")
    assert s.drain_injections() == ["a", "b"]
    assert s.drain_injections() == []
