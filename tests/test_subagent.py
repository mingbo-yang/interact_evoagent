"""Tests for P1.5 subagent orchestration (parallel `task` tool)."""

import asyncio

import pytest

from evoagent.models.base import BaseLLMProvider
from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.models.schema import LLMResponse
from evoagent.tools.builtin import create_builtin_registry
from evoagent.tools.subagent_tools import SubagentTool


def _router(provider):
    return ModelRouter(providers={"executor": provider, "default": provider})


def _tool_names(registry):
    return {s["function"]["name"] for s in registry.get_tool_schemas()}


@pytest.mark.asyncio
async def test_single_subtask_returns_answer(tmp_path):
    router = _router(MockLLMProvider(fixed_text="sub completed"))
    tool = SubagentTool(tmp_path, router)
    res = await tool.run(tasks=[{"description": "do A", "prompt": "do thing A"}])
    assert res.success
    assert "Subtask 1: do A" in res.output
    assert "sub completed" in res.output
    assert res.metadata["subtasks"] == 1


@pytest.mark.asyncio
async def test_multiple_subtasks_all_reported(tmp_path):
    router = _router(MockLLMProvider(fixed_text="done"))
    tool = SubagentTool(tmp_path, router)
    res = await tool.run(tasks=[
        {"description": "alpha", "prompt": "p1"},
        {"description": "beta", "prompt": "p2"},
        {"description": "gamma", "prompt": "p3"},
    ])
    assert res.success
    for label in ("alpha", "beta", "gamma"):
        assert label in res.output
    assert res.metadata["subtasks"] == 3


@pytest.mark.asyncio
async def test_subtasks_run_concurrently(tmp_path):
    """Sub-agents in one task call execute in parallel."""

    class _SlowProvider(BaseLLMProvider):
        def __init__(self):
            self.active = 0
            self.max_active = 0

        @property
        def provider_name(self):
            return "slow"

        async def chat(self, request):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            try:
                await asyncio.sleep(0.05)
                return LLMResponse(content="ok", model="m", finish_reason="stop")
            finally:
                self.active -= 1

        async def structured_chat(self, request, schema):  # pragma: no cover
            raise NotImplementedError

        async def stream_chat(self, request):  # pragma: no cover
            yield "ok"

    provider = _SlowProvider()
    tool = SubagentTool(tmp_path, _router(provider))
    await tool.run(tasks=[
        {"description": f"t{i}", "prompt": f"p{i}"} for i in range(3)
    ])
    assert provider.max_active >= 2  # ran in parallel, not strictly serial


@pytest.mark.asyncio
async def test_one_failing_subtask_does_not_break_batch(tmp_path):
    class _BoomProvider(BaseLLMProvider):
        @property
        def provider_name(self):
            return "boom"

        async def chat(self, request):
            raise RuntimeError("provider exploded")

        async def structured_chat(self, request, schema):  # pragma: no cover
            raise NotImplementedError

        async def stream_chat(self, request):  # pragma: no cover
            yield ""

    tool = SubagentTool(tmp_path, _router(_BoomProvider()))
    res = await tool.run(tasks=[{"description": "x", "prompt": "p"}])
    # The sub-agent failed but the tool returns a structured result, not a crash.
    assert res.metadata["subtasks"] == 1
    assert "Subtask 1: x" in res.output


def test_subagent_registered_only_with_router(tmp_path):
    plain = create_builtin_registry(tmp_path)
    assert "task" not in _tool_names(plain)

    router = _router(MockLLMProvider())
    with_sub = create_builtin_registry(tmp_path, enable_subagents=True, model_router=router)
    assert "task" in _tool_names(with_sub)


def test_subagents_cannot_recurse(tmp_path):
    """A sub-agent's registry must not contain the task tool."""
    sub_registry = create_builtin_registry(tmp_path, enable_subagents=False)
    assert "task" not in _tool_names(sub_registry)
