"""Tests for P1.7 crash-recovery checkpoints and resume (core/checkpoint.py)."""

import pytest

from evoagent.core.agent import Agent
from evoagent.core.checkpoint import CheckpointStore, RunCheckpointer
from evoagent.core.message import Message, MessageRole, ToolCall
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
        return LLMResponse(content="done", model="m", finish_reason="stop")

    async def structured_chat(self, request, schema):  # pragma: no cover
        raise NotImplementedError

    async def stream_chat(self, request):  # pragma: no cover
        yield "done"


def _router(provider):
    return ModelRouter(providers={"executor": provider, "default": provider})


def test_checkpointer_atomic_save_and_load(tmp_path):
    cp = RunCheckpointer(tmp_path / "run1", "run1", task="do x")
    msgs = [
        Message(role=MessageRole.USER, content="hello"),
        Message(role=MessageRole.ASSISTANT, content="hi"),
    ]
    cp.save(msgs, status="running")
    data = RunCheckpointer.load(tmp_path / "run1")
    assert data is not None
    assert data["run_id"] == "run1"
    assert data["task"] == "do x"
    assert data["status"] == "running"
    assert len(data["messages"]) == 2
    assert not (tmp_path / "run1" / "checkpoint.json.tmp").exists()


def test_checkpoint_store_latest(tmp_path):
    store = CheckpointStore(tmp_path)
    store.checkpointer("a", "task a").save([Message(role=MessageRole.USER, content="a")])
    store.checkpointer("b", "task b").save([Message(role=MessageRole.USER, content="b")])
    assert set(store.list_runs()) == {"a", "b"}
    latest = store.latest()
    assert latest is not None
    assert latest["run_id"] in {"a", "b"}


def test_checkpoint_redacts_secrets(tmp_path):
    cp = RunCheckpointer(tmp_path / "r", "r")
    cp.save([Message(role=MessageRole.USER,
                     content="my key is sk-abcdef1234567890abcdef")])
    raw = (tmp_path / "r" / "checkpoint.json").read_text()
    assert "sk-abcdef1234567890abcdef" not in raw
    assert "REDACTED" in raw


def test_load_missing_returns_none(tmp_path):
    assert RunCheckpointer.load(tmp_path / "nope") is None
    assert CheckpointStore(tmp_path).latest() is None


@pytest.mark.asyncio
async def test_agent_run_writes_checkpoint(tmp_path):
    provider = ScriptedProvider([
        LLMResponse(content="", model="m", tool_calls=[
            ToolCall(id="c1", name="list_directory", arguments={"path": "."}),
        ]),
        LLMResponse(content="All done.", model="m", finish_reason="stop"),
    ])
    registry = create_builtin_registry(tmp_path)
    cp_dir = tmp_path / "runs"
    agent = Agent(model_router=_router(provider), tool_registry=registry,
                  workspace=tmp_path, checkpoint_dir=cp_dir)
    result = await agent.run("list files")
    assert result.success
    data = CheckpointStore(cp_dir).load(result.run_id)
    assert data is not None
    assert data["status"] == "done"
    assert data["stop_reason"] == "final"


@pytest.mark.asyncio
async def test_resume_continues_to_completion(tmp_path):
    """Simulate a crash after one tool round, then resume to a final answer."""
    registry = create_builtin_registry(tmp_path)
    cp_dir = tmp_path / "runs"
    run_id = "crashed-run"
    messages = [
        Message(role=MessageRole.USER, content="list the files"),
        Message(role=MessageRole.ASSISTANT, content="", tool_calls=[
            ToolCall(id="c1", name="list_directory", arguments={"path": "."}),
        ]),
        Message(role=MessageRole.TOOL, tool_call_id="c1", name="list_directory",
                content="(empty)"),
    ]
    CheckpointStore(cp_dir).checkpointer(run_id, "list the files").save(
        messages, status="running", system_prompt="You are EvoAgent."
    )

    provider = ScriptedProvider([
        LLMResponse(content="Resumed and finished.", model="m", finish_reason="stop"),
    ])
    agent = Agent(model_router=_router(provider), tool_registry=registry,
                  workspace=tmp_path, checkpoint_dir=cp_dir)
    result = await agent.resume(run_id)
    assert result.success
    assert result.final_answer == "Resumed and finished."
    assert provider.calls == 1
    data = CheckpointStore(cp_dir).load(run_id)
    assert data["status"] == "done"


@pytest.mark.asyncio
async def test_resume_with_follow_up(tmp_path):
    registry = create_builtin_registry(tmp_path)
    cp_dir = tmp_path / "runs"
    run_id = "r2"
    CheckpointStore(cp_dir).checkpointer(run_id, "orig").save(
        [Message(role=MessageRole.USER, content="orig task")], status="interrupted"
    )
    provider = ScriptedProvider([
        LLMResponse(content="handled follow-up", model="m", finish_reason="stop"),
    ])
    agent = Agent(model_router=_router(provider), tool_registry=registry,
                  workspace=tmp_path, checkpoint_dir=cp_dir)
    result = await agent.resume(run_id, follow_up="now also do Y")
    assert result.success
    assert result.final_answer == "handled follow-up"


@pytest.mark.asyncio
async def test_resume_without_checkpoint_dir_raises(tmp_path):
    registry = create_builtin_registry(tmp_path)
    agent = Agent(model_router=_router(ScriptedProvider([])), tool_registry=registry,
                  workspace=tmp_path)
    with pytest.raises(ValueError):
        await agent.resume("whatever")


@pytest.mark.asyncio
async def test_resume_missing_run_raises(tmp_path):
    registry = create_builtin_registry(tmp_path)
    agent = Agent(model_router=_router(ScriptedProvider([])), tool_registry=registry,
                  workspace=tmp_path, checkpoint_dir=tmp_path / "runs")
    with pytest.raises(ValueError):
        await agent.resume("does-not-exist")
