"""Regression tests for bugs found during the v0.5.0 deep audit.

Each test targets a concrete bug that real-API / real-execution exposed but
the mock-based suite did not catch.
"""

import os
from pathlib import Path

import pytest

from evoagent.conversation.runtime import ConversationRuntime
from evoagent.conversation.session import ConversationSession
from evoagent.core.agent import Agent
from evoagent.core.errors import ModelProviderError
from evoagent.core.message import Message, MessageRole
from evoagent.core.state import RuntimeState, StepResult
from evoagent.models.factory import MockLLMProvider, ProviderFactory
from evoagent.models.openai_compatible import OpenAICompatibleProvider
from evoagent.models.router import ModelRouter
from evoagent.models.schema import LLMRequest, ModelConfig
from evoagent.planning.planner import Planner
from evoagent.planning.schema import ActionType, Plan, PlanStep
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.tools.builtin import create_builtin_registry


def test_planner_format_tools_exposes_real_param_names():
    """Planner must give the LLM each tool's real parameter names, otherwise
    the model guesses (file_path vs path) and tool calls fail validation."""
    schema = [{
        "function": {
            "name": "edit_file",
            "description": "Find and replace text in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        }
    }]
    text = Planner._format_tools(schema)
    assert "edit_file" in text
    assert "path" in text
    assert "old_text" in text and "new_text" in text
    # The wrong (guessed) name must not be what we advertise.
    assert "file_path" not in text


def test_build_final_answer_skips_finish_placeholder():
    """_build_final_answer must not return the FINISH step's constant
    placeholder when a real answer exists earlier in the run."""
    mock = MockLLMProvider(fixed_text="OK")
    router = ModelRouter(providers={"default": mock})
    agent = Agent(model_router=router, workspace=".")
    state = RuntimeState(run_id="r1", task="t")
    state.plan = Plan(id="p1", task="t", steps=[
        PlanStep(id="s1", goal="real", action_type=ActionType.TOOL, tool_name="x"),
        PlanStep(id="s2", goal="finish", action_type=ActionType.FINISH),
    ])
    state.add_step_result(StepResult(step_id="s1", success=True, output="THE REAL ANSWER"))
    state.add_step_result(StepResult(step_id="s2", success=True, output="Task finished."))
    assert agent._loop._build_final_answer(state) == "THE REAL ANSWER"


@pytest.mark.asyncio
async def test_stream_records_real_user_message():
    """Streaming turn record must keep the user's message, not overwrite it
    with the assistant response."""
    session = ConversationSession(workspace=".")
    mock = MockLLMProvider(fixed_text="ASSISTANT_REPLY")
    router = ModelRouter(providers={"executor": mock, "default": mock})
    tools = create_builtin_registry(Path("."))
    runtime = ConversationRuntime(session, router, tools, PermissionPolicy())

    async for _ in runtime.handle_user_message_stream("USER_QUESTION"):
        pass

    assert session.turns[-1].user_message == "USER_QUESTION"
    assert session.turns[-1].assistant_response == "ASSISTANT_REPLY"


def test_factory_rejects_native_anthropic_and_gemini():
    """Anthropic/Gemini use native schemas; routing them through the
    OpenAI-compatible adapter silently 400s. Factory must fail clearly."""
    for prov in ("anthropic", "gemini"):
        cfg = ModelConfig(provider=prov, adapter_type=prov, base_url="https://example.invalid")
        with pytest.raises(ModelProviderError):
            ProviderFactory.create(cfg)


def test_payload_omits_reasoning_content():
    """reasoning_content (DeepSeek CoT) must never be echoed back in the
    outgoing request payload."""
    os.environ["AUDIT_TEST_KEY"] = "k"
    cfg = ModelConfig(
        provider="openai_compatible", adapter_type="openai_compatible",
        base_url="https://example.invalid", api_key_env="AUDIT_TEST_KEY",
    )
    provider = OpenAICompatibleProvider(cfg)
    req = LLMRequest(messages=[
        Message(role=MessageRole.ASSISTANT, content="hi", reasoning_content="SECRET_COT"),
    ])
    payload = provider._build_payload(req, stream=False)
    for m in payload["messages"]:
        assert "reasoning_content" not in m


@pytest.mark.asyncio
async def test_sandbox_ask_is_fail_closed_by_default():
    """ASK commands must NOT execute without approval; with auto_approve they do."""
    import tempfile

    from evoagent.sandbox.local import LocalSandbox
    from evoagent.sandbox.workspace import Workspace

    with tempfile.TemporaryDirectory() as tmp:
        ws = Workspace(tmp)
        # "true" is not allow-listed -> AUTO high-risk -> ASK
        blocked = LocalSandbox(workspace=ws, policy=PermissionPolicy(), auto_approve=False)
        res = await blocked.run_shell("true")
        assert not res.success
        assert "not auto-approved" in res.stderr.lower()

        approved = LocalSandbox(workspace=ws, policy=PermissionPolicy(), auto_approve=True)
        res2 = await approved.run_shell("true")
        assert res2.success


@pytest.mark.asyncio
async def test_bash_tool_ask_fail_closed_by_default():
    """Built-in bash tool refuses ASK commands unless auto_approve is set."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        reg = create_builtin_registry(Path(tmp))  # auto_approve defaults False
        bash = reg.get("bash")
        result = await bash.run(command="true")
        assert not result.success
        assert result.metadata.get("decision") == "ask"


def test_patchmanager_rejects_workspace_escape():
    """PatchManager must not write outside the workspace."""
    import tempfile

    from evoagent.code.patch import PatchManager

    with tempfile.TemporaryDirectory() as tmp:
        pm = PatchManager(tmp)
        msg = pm.write_file("../escaped.txt", "HACKED")
        assert "escapes workspace" in msg.lower()
        assert not (Path(tmp).parent / "escaped.txt").exists()
        msg2 = pm.edit_file("/etc/hosts", "a", "b")
        assert "escapes workspace" in msg2.lower()

def test_consolidate_clustered_duplicates_no_keyerror():
    """Clustered/transitive duplicates must not raise KeyError when a merged
    memory is revisited."""
    import tempfile

    from evoagent.memory.consolidation import MemoryConsolidator
    from evoagent.memory.schema import MemoryItem, MemoryType
    from evoagent.memory.sqlite_store import SQLiteMemoryStore

    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteMemoryStore(Path(tmp) / "m.sqlite")
        try:
            for _ in range(3):
                store.add(MemoryItem(memory_type=MemoryType.EPISODIC,
                                     content="list files in the directory", importance=0.5))
            c = MemoryConsolidator(store, similarity_threshold=0.4)
            merges = c.consolidate()  # must not raise
            assert merges >= 1
            assert len(store.list(limit=100)) == 1
        finally:
            store.close()


def test_chunker_rejects_zero_size_and_terminates():
    """chunk_size<=0 must raise; overlap>=size must still terminate."""
    from evoagent.rag.chunker import SimpleTextChunker

    with pytest.raises(ValueError):
        SimpleTextChunker(chunk_size=0)
    # overlap >= size should not loop forever.
    chunks = SimpleTextChunker(chunk_size=10, chunk_overlap=20).chunk_text("hello world foo", "d1")
    assert len(chunks) >= 1


def test_mock_embedding_fills_all_dims():
    """Every embedding dimension must carry real signal, not zero padding."""
    from evoagent.retrieval.embeddings import MockEmbeddingModel

    vec = MockEmbeddingModel().embed_text("hello world")
    assert len(vec) == 64
    non_zero = sum(1 for v in vec if v != 0.0)
    assert non_zero >= 60  # previously only 8 were non-zero


def test_keyword_index_cjk_is_searchable():
    """CJK documents/queries must be retrievable (not silently dropped)."""
    from evoagent.retrieval.keyword import KeywordRetriever

    idx = KeywordRetriever()
    idx.add_items([{"id": "a", "text": "你好世界，这是一个测试"}])
    results = idx.search("你好")
    assert any(r["id"] == "a" for r in results)

@pytest.mark.asyncio
async def test_workflow_deadend_sets_failed_status():
    """A non-finish node with no matching outgoing edge must end in FAILED,
    not leave the run stuck in RUNNING."""
    from evoagent.core.state import RunStatus, RuntimeState
    from evoagent.workflow.graph import WorkflowGraph
    from evoagent.workflow.node import WorkflowNode
    from evoagent.workflow.runtime import WorkflowRuntime

    async def _noop(state, ctx):
        return state

    graph = WorkflowGraph()
    graph.add_node(WorkflowNode(name="a", handler=_noop))
    graph.add_node(WorkflowNode(name="b", handler=_noop))
    graph.set_entrypoint("a")
    graph.set_finish("b")  # 'a' has no edge to 'b' -> dead end
    runtime = WorkflowRuntime(graph)
    result = await runtime.run(RuntimeState(run_id="dead", task="t"))
    assert result.status == RunStatus.FAILED
    assert any("no matching outgoing edge" in e for e in result.errors)


@pytest.mark.asyncio
async def test_workflow_success_has_no_false_max_steps_error():
    """A run that finishes on the boundary step must not be flagged with a
    spurious 'Max steps' error."""
    from evoagent.core.state import RunStatus, RuntimeState
    from evoagent.workflow.graph import WorkflowGraph
    from evoagent.workflow.node import WorkflowNode
    from evoagent.workflow.runtime import WorkflowRuntime

    async def _noop(state, ctx):
        return state

    graph = WorkflowGraph()
    graph.add_node(WorkflowNode(name="only", handler=_noop))
    graph.set_entrypoint("only")
    graph.set_finish("only")
    runtime = WorkflowRuntime(graph, max_steps=1)
    result = await runtime.run(RuntimeState(run_id="ok", task="t"))
    assert result.status == RunStatus.SUCCEEDED
    assert not any("Max steps" in e for e in result.errors)


@pytest.mark.asyncio
async def test_builtin_plan_node_uses_real_planner():
    """The built-in 'plan' workflow node must delegate to the Planner in ctx,
    not just set a flag."""
    from evoagent.core.state import RuntimeState
    from evoagent.planning.planner import Planner
    from evoagent.workflow.builtin_nodes import make_builtin_nodes

    mock = MockLLMProvider(
        fixed_text='{"risk_level":"low","steps":[{"goal":"do","action_type":"finish"}]}'
    )
    nodes = make_builtin_nodes()
    state = RuntimeState(run_id="w", task="say hi")
    ctx = {"planner": Planner(llm=mock), "tool_registry": None}
    result = await nodes["plan"].execute(state, ctx)
    assert result.plan is not None
    assert len(result.plan.steps) >= 1
