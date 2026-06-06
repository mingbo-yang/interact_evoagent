"""Tests for context management: token estimation + compaction (P0.6)."""

import pytest

from evoagent.conversation.context import (
    compact_messages,
    estimate_tokens,
    message_tokens,
    messages_tokens,
    summarize_dropped,
)
from evoagent.core.message import Message, MessageRole, ToolCall
from evoagent.core.react import ReActEngine, safe_messages
from evoagent.models.base import BaseLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.models.schema import LLMResponse
from evoagent.tools.builtin import create_builtin_registry


class ScriptedProvider(BaseLLMProvider):
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "scripted"

    async def chat(self, request):
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(content="done", model="scripted", finish_reason="stop")

    async def structured_chat(self, request, schema):  # pragma: no cover
        raise NotImplementedError

    async def stream_chat(self, request):  # pragma: no cover
        yield "done"


def _big(role, content, n=4000):
    return Message(role=role, content=content * n)


def _is_valid(messages):
    """Provider-safe: compacting again drops nothing."""
    return len(safe_messages(messages, window=0)) == len(messages)


def test_estimate_and_message_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 40) == 10
    m = Message(role=MessageRole.USER, content="x" * 40)
    assert message_tokens(m) >= 10
    msgs = [m, Message(role=MessageRole.ASSISTANT, content="y" * 40)]
    assert messages_tokens(msgs) == message_tokens(msgs[0]) + message_tokens(msgs[1])


def test_compact_noop_under_budget():
    msgs = [Message(role=MessageRole.USER, content="hello")]
    out, changed = compact_messages(msgs, token_budget=10_000)
    assert changed is False
    assert out is msgs


def test_compact_triggers_and_preserves_state():
    msgs = [
        Message(role=MessageRole.USER, content="Fix the bug in app.py so tests pass."),
        Message(role=MessageRole.ASSISTANT, content="", tool_calls=[
            ToolCall(id="c1", name="edit_file", arguments={"path": "app.py"})]),
        Message(role=MessageRole.TOOL, tool_call_id="c1", name="edit_file",
                content="error: patch failed " + "z" * 20000),
        _big(MessageRole.ASSISTANT, "thinking "),
        _big(MessageRole.USER, "more context "),
        Message(role=MessageRole.ASSISTANT, content="Latest progress: almost done."),
    ]
    out, changed = compact_messages(
        msgs, token_budget=2_000, keep_recent_tokens=500)
    assert changed is True
    assert messages_tokens(out) < messages_tokens(msgs)
    summary = out[0].content
    assert out[0].metadata.get("compacted") is True
    assert "Fix the bug in app.py" in summary
    assert "app.py" in summary  # file changed surfaced
    assert "fail" in summary.lower() or "error" in summary.lower()
    assert _is_valid(out)


def test_compact_keeps_group_integrity():
    # Cut point must not split an assistant/tool group.
    msgs = [
        _big(MessageRole.USER, "task "),
        Message(role=MessageRole.ASSISTANT, content="", tool_calls=[
            ToolCall(id="t1", name="bash", arguments={})]),
        _big(MessageRole.TOOL, "huge output ", n=8000),
        Message(role=MessageRole.ASSISTANT, content="done note"),
    ]
    # set tool_call_id on the tool message
    msgs[2].tool_call_id = "t1"
    msgs[2].name = "bash"
    out, changed = compact_messages(msgs, token_budget=1_000, keep_recent_tokens=100)
    assert changed is True
    assert _is_valid(out)


def test_summarize_includes_extra_state():
    dropped = [Message(role=MessageRole.USER, content="do a thing")]
    text = summarize_dropped(dropped, extra_state="Current task list:\n[~] step 1")
    assert "do a thing" in text
    assert "step 1" in text


@pytest.mark.asyncio
async def test_engine_compacts_during_run(tmp_path):
    reg = create_builtin_registry(tmp_path)
    provider = ScriptedProvider([LLMResponse(content="all done", model="s",
                                             finish_reason="stop")])
    router = ModelRouter(providers={"executor": provider, "default": provider})
    engine = ReActEngine(router, reg, role="executor",
                         token_budget=1_000, keep_recent_tokens=200)
    messages = [
        _big(MessageRole.USER, "huge task "),
        _big(MessageRole.ASSISTANT, "huge reply "),
        Message(role=MessageRole.USER, content="now finish"),
    ]
    result = await engine.run_turn(messages, tools_schema=[])
    assert result.success
    assert result.compactions >= 1
    assert _is_valid(result.messages)


@pytest.mark.asyncio
async def test_engine_no_compaction_when_disabled(tmp_path):
    reg = create_builtin_registry(tmp_path)
    provider = ScriptedProvider([LLMResponse(content="done", model="s",
                                             finish_reason="stop")])
    router = ModelRouter(providers={"executor": provider, "default": provider})
    engine = ReActEngine(router, reg, role="executor",
                         token_budget=1_000, enable_compaction=False)
    messages = [_big(MessageRole.USER, "huge ")]
    result = await engine.run_turn(messages, tools_schema=[])
    assert result.compactions == 0


def test_safe_messages_pins_compacted_anchor():
    # A long kept window must never push the summary out of the request.
    anchor = Message(role=MessageRole.USER, content="SUMMARY of earlier work",
                     metadata={"compacted": True})
    rest = [Message(role=MessageRole.USER, content=f"m{i}") for i in range(60)]
    out = safe_messages([anchor, *rest], window=50)
    assert out[0] is anchor
    assert len(out) == 51  # anchor + last 50


def test_compact_preserves_later_user_instructions():
    msgs = [
        Message(role=MessageRole.USER, content="Build feature X."),
        _big(MessageRole.ASSISTANT, "work "),
        Message(role=MessageRole.USER, content="Important: do not touch module Y."),
        _big(MessageRole.ASSISTANT, "more work "),
        Message(role=MessageRole.USER, content="now continue"),
    ]
    out, changed = compact_messages(msgs, token_budget=1_500, keep_recent_tokens=200)
    assert changed is True
    summary = out[0].content
    assert "Build feature X." in summary
    assert "do not touch module Y" in summary


def test_compact_no_progress_returns_unchanged():
    # A single huge recent message cannot be dropped; after replacing a tiny
    # prior prefix the total does not shrink, so compaction must be a no-op.
    prior = Message(role=MessageRole.USER, content="x" * 40,
                    metadata={"compacted": True})
    huge = _big(MessageRole.ASSISTANT, "z", n=40000)
    out, changed = compact_messages([prior, huge], token_budget=1_000,
                                    keep_recent_tokens=200)
    assert changed is False

