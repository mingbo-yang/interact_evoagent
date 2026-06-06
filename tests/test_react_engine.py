"""Regression tests for the canonical ReActEngine (P0.1 loop consolidation)."""

import pytest

from evoagent.core.agent import Agent
from evoagent.core.message import Message, MessageRole, ToolCall
from evoagent.core.react import ReActEngine, classify_tool, safe_messages
from evoagent.models.base import BaseLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.models.schema import LLMResponse
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.sandbox.schema import PermissionMode, PolicyConfig
from evoagent.tools.builtin import create_builtin_registry


class ScriptedProvider(BaseLLMProvider):
    """Returns a queued sequence of LLMResponses, one per chat() call."""

    def __init__(self, responses: list[LLMResponse]):
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


def _router(provider) -> ModelRouter:
    return ModelRouter(providers={"executor": provider, "default": provider})


# ── safe_messages ───────────────────────────────────────────────────────


def test_safe_messages_keeps_all_parallel_tool_responses():
    msgs = [
        Message(role=MessageRole.USER, content="go"),
        Message(role=MessageRole.ASSISTANT, content="", tool_calls=[
            ToolCall(id="a", name="list_directory", arguments={}),
            ToolCall(id="b", name="bash", arguments={}),
        ]),
        Message(role=MessageRole.TOOL, tool_call_id="a", name="list_directory", content="out_a"),
        Message(role=MessageRole.TOOL, tool_call_id="b", name="bash", content="out_b"),
    ]
    safe = safe_messages(msgs)
    tool_ids = {m.tool_call_id for m in safe if m.role == MessageRole.TOOL}
    assert tool_ids == {"a", "b"}


def test_safe_messages_drops_incomplete_group():
    msgs = [
        Message(role=MessageRole.USER, content="go"),
        Message(role=MessageRole.ASSISTANT, content="", tool_calls=[
            ToolCall(id="x", name="list_directory", arguments={}),
            ToolCall(id="y", name="bash", arguments={}),
        ]),
        Message(role=MessageRole.TOOL, tool_call_id="x", name="list_directory", content="only one"),
    ]
    safe = safe_messages(msgs)
    assert all(not (m.role == MessageRole.ASSISTANT and m.tool_calls) for m in safe)
    assert all(m.role != MessageRole.TOOL for m in safe)


def test_safe_messages_drops_extra_unmatched_tool_messages():
    """An extra tool message for an unknown id must be dropped, and only one
    response per required id is kept."""
    msgs = [
        Message(role=MessageRole.USER, content="go"),
        Message(role=MessageRole.ASSISTANT, content="", tool_calls=[
            ToolCall(id="a", name="list_directory", arguments={}),
        ]),
        Message(role=MessageRole.TOOL, tool_call_id="a", name="list_directory", content="first"),
        Message(role=MessageRole.TOOL, tool_call_id="a", name="list_directory", content="dup"),
        Message(role=MessageRole.TOOL, tool_call_id="zzz", name="bash", content="orphan"),
    ]
    safe = safe_messages(msgs)
    tool_msgs = [m for m in safe if m.role == MessageRole.TOOL]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].content == "first"


def test_classify_tool_maps_bash_to_shell():
    assert classify_tool("bash", {"command": "rm -rf /"})[0] == "shell"
    assert classify_tool("write_file", {"path": "x"})[0] == "file_write"
    assert classify_tool("read_file", {"path": "x"})[0] == "file_read"


# ── engine ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_engine_reaches_final_answer(tmp_path):
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="c1", name="list_directory", arguments={"path": "."}),
        ]),
        LLMResponse(content="All done.", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    engine = ReActEngine(_router(provider), registry, ask_fallback="allow")
    messages = [Message(role=MessageRole.USER, content="list files")]
    result = await engine.run_turn(messages)
    assert result.success
    assert result.stop_reason == "final"
    assert result.final_text == "All done."
    assert result.tool_calls == 1
    assert result.llm_calls == 2


@pytest.mark.asyncio
async def test_engine_one_tool_succeeds_one_fails_both_answered(tmp_path):
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="ok", name="list_directory", arguments={"path": "."}),
            ToolCall(id="bad", name="read_file", arguments={"path": "does_not_exist.xyz"}),
        ]),
        LLMResponse(content="recovered", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    engine = ReActEngine(_router(provider), registry, ask_fallback="allow")
    messages = [Message(role=MessageRole.USER, content="do two")]
    result = await engine.run_turn(messages)
    # Both tool calls answered with a tool message for each id.
    answered = {m.tool_call_id for m in messages if m.role == MessageRole.TOOL}
    assert answered == {"ok", "bad"}
    # Model recovered to a final answer → operationally successful.
    assert result.success
    assert result.final_text == "recovered"


@pytest.mark.asyncio
async def test_engine_tool_exception_keeps_history_safe(tmp_path):
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="z", name="nonexistent_tool", arguments={}),
        ]),
        LLMResponse(content="ok", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    engine = ReActEngine(_router(provider), registry, ask_fallback="allow")
    messages = [Message(role=MessageRole.USER, content="call missing tool")]
    result = await engine.run_turn(messages)
    # Even though the tool raised, the call got a tool message.
    assert any(m.role == MessageRole.TOOL and m.tool_call_id == "z" for m in messages)
    # safe_messages over the resulting history must be provider-valid.
    safe = safe_messages(messages)
    _assert_groups_answered(safe)
    assert result.success


@pytest.mark.asyncio
async def test_engine_max_tool_rounds_is_unsuccessful(tmp_path):
    # Provider always asks for a tool → never finishes.
    looping = ScriptedProvider([])

    async def always_tool(request):
        looping.calls += 1
        return LLMResponse(content="", model="m", tool_calls=[
            ToolCall(name="list_directory", arguments={"path": "."}),
        ])

    looping.chat = always_tool  # type: ignore[assignment]
    registry = create_builtin_registry(tmp_path)
    engine = ReActEngine(_router(looping), registry, ask_fallback="allow", max_tool_rounds=3)
    messages = [Message(role=MessageRole.USER, content="loop")]
    result = await engine.run_turn(messages)
    assert not result.success
    assert result.stop_reason == "max_tool_rounds"


@pytest.mark.asyncio
async def test_engine_deny_rule_blocks_tool(tmp_path):
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="d", name="bash", arguments={"command": "rm -rf /tmp/x"}),
        ]),
        LLMResponse(content="blocked", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    # ask_fallback=allow must NOT override an explicit deny rule.
    engine = ReActEngine(_router(provider), registry, ask_fallback="allow")
    messages = [Message(role=MessageRole.USER, content="delete")]
    result = await engine.run_turn(messages)
    tool_msg = next(m for m in messages if m.role == MessageRole.TOOL)
    assert "denied" in tool_msg.content.lower()
    assert any("permission denied" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_engine_provider_error_is_unsuccessful(tmp_path):
    class Boom(BaseLLMProvider):
        @property
        def provider_name(self):
            return "boom"

        async def chat(self, request):
            raise RuntimeError("network down")

        async def structured_chat(self, request, schema):
            raise NotImplementedError

        async def stream_chat(self, request):
            yield ""

    registry = create_builtin_registry(tmp_path)
    engine = ReActEngine(_router(Boom()), registry)
    result = await engine.run_turn([Message(role=MessageRole.USER, content="x")])
    assert not result.success
    assert result.stop_reason == "provider_error"


# ── Agent.run integration ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_run_uses_iterative_loop(tmp_path):
    (tmp_path / "hello.txt").write_text("hi")
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="c1", name="list_directory", arguments={"path": "."}),
        ]),
        LLMResponse(content="Found hello.txt", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    agent = Agent(model_router=_router(provider), tool_registry=registry, workspace=tmp_path)
    result = await agent.run("list the files")
    assert result.success
    assert result.final_answer == "Found hello.txt"
    assert result.tool_calls == 1
    assert result.state is not None
    assert len(result.state.tool_results) == 1


@pytest.mark.asyncio
async def test_agent_run_cost_not_cumulative(tmp_path):
    """Each run gets a fresh cost snapshot → totals are per-run."""
    def make_provider():
        return ScriptedProvider([
            LLMResponse(content="answer", model="m", finish_reason="stop",
                        usage={"prompt_tokens": 10, "completion_tokens": 5}),
        ])

    registry = create_builtin_registry(tmp_path)
    p1 = make_provider()
    agent = Agent(model_router=_router(p1), tool_registry=registry, workspace=tmp_path)
    r1 = await agent.run("first")
    # second run with a fresh scripted provider
    agent.model_router = _router(make_provider())
    r2 = await agent.run("second")
    assert r1.total_tokens == r2.total_tokens == 15


@pytest.mark.asyncio
async def test_agent_run_ask_auto_approved_non_interactive(tmp_path):
    """A tool that maps to an ASK decision is auto-approved in Agent.run."""
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="i", name="bash", arguments={"command": "pip install nothing-xyz"}),
        ]),
        LLMResponse(content="installed", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    # AUTO mode: '*install*' is an ASK rule; Agent.run uses ask_fallback=allow.
    policy = PermissionPolicy(PolicyConfig(mode=PermissionMode.AUTO))
    agent = Agent(model_router=_router(provider), tool_registry=registry,
                  workspace=tmp_path, permission_policy=policy)
    result = await agent.run("install a package")
    # The bash tool actually ran (it was not blocked by 'approval required').
    tool_msg = next(m for m in result.state.messages if m.role == MessageRole.TOOL)
    assert "approval required" not in tool_msg.content.lower()


def _assert_groups_answered(messages: list[Message]) -> None:
    i = 0
    while i < len(messages):
        m = messages[i]
        if m.role == MessageRole.ASSISTANT and m.tool_calls:
            required = {tc.id for tc in m.tool_calls}
            answered = set()
            j = i + 1
            while j < len(messages) and messages[j].role == MessageRole.TOOL:
                answered.add(messages[j].tool_call_id)
                j += 1
            assert required.issubset(answered)
            i = j
            continue
        assert m.role != MessageRole.TOOL
        i += 1
