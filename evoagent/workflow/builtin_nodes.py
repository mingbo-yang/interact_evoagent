"""Built-in workflow nodes wrapping Planner/Executor/Critic/Memory.

Each node delegates to the corresponding subsystem when it is supplied in the
node context (``ctx``). Expected ctx keys:
    - ``planner``: a Planner instance
    - ``executor``: an Executor instance
    - ``critic``: a Critic instance
    - ``tool_registry``: a ToolRegistry (for tool schemas)
    - ``memory_store``: a BaseMemoryStore
When a component is absent the node degrades gracefully (records a metadata
flag and passes the state through) so partial graphs still run.
"""

from typing import Any

from evoagent.core.state import RunStatus, RuntimeState
from evoagent.workflow.node import WorkflowNode


async def _passthrough(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    return state


async def _load_context(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Load context from config or ctx dict."""
    system_prompt = ctx.get("system_prompt", "You are a helpful assistant.")
    state.metadata["system_prompt"] = system_prompt
    return state


async def _retrieve_memory(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Retrieve relevant memories for the task and add them to the context."""
    state.metadata["memory_requested"] = True
    store = ctx.get("memory_store")
    if store is None:
        return state
    try:
        from evoagent.memory.retriever import MemoryRetriever

        retriever = MemoryRetriever(store)
        memories = retriever.retrieve(state.task)
        state.metadata["memory_context"] = retriever.format_for_prompt(memories)
    except Exception as e:
        state.add_error(f"retrieve_memory failed: {e}")
    return state


async def _plan_node(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Create an execution plan via the Planner."""
    state.metadata["plan_requested"] = True
    planner = ctx.get("planner")
    if planner is None:
        return state
    try:
        tool_registry = ctx.get("tool_registry")
        tools_schema = tool_registry.get_tool_schemas() if tool_registry else []
        context = state.metadata.get("memory_context", "")
        state.plan = await planner.plan(state.task, tools_schema, context=context)
        state.metadata["workflow_step_index"] = 0
    except Exception as e:
        state.add_error(f"plan failed: {e}")
    return state


async def _execute_step(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Execute the next pending plan step via the Executor."""
    state.metadata["step_executed"] = True
    executor = ctx.get("executor")
    if executor is None or state.plan is None:
        return state
    try:
        idx = state.metadata.get("workflow_step_index", 0)
        steps = state.plan.steps
        if idx >= len(steps):
            return state
        step = steps[idx]
        await executor.execute_step(state, step)
        state.metadata["workflow_step_index"] = idx + 1
    except Exception as e:
        state.add_error(f"execute_step failed: {e}")
    return state


async def _critic_node(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Evaluate the most recent step result via the Critic."""
    state.metadata["critic_done"] = True
    critic = ctx.get("critic")
    if critic is None or state.plan is None or not state.step_results:
        return state
    try:
        idx = max(0, state.metadata.get("workflow_step_index", 1) - 1)
        step = state.plan.steps[idx] if idx < len(state.plan.steps) else state.plan.steps[-1]
        decision = await critic.evaluate(state.task, step, state.step_results[-1])
        state.metadata["critic_passed"] = bool(getattr(decision, "passed", False))
    except Exception as e:
        state.add_error(f"critic failed: {e}")
    return state


async def _memory_write(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Persist memories from this run via the MemoryWriter."""
    state.metadata["memory_written"] = True
    store = ctx.get("memory_store")
    if store is None:
        return state
    try:
        from evoagent.memory.writer import MemoryWriter

        writer = MemoryWriter(store)
        success = state.status != RunStatus.FAILED and not state.errors
        writer.write_from_run(state, success)
    except Exception as e:
        state.add_error(f"memory_write failed: {e}")
    return state


async def _finish_node(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Mark task as finished."""
    state.metadata["finished"] = True
    return state


def make_builtin_nodes() -> dict[str, WorkflowNode]:
    """Create a dict of built-in workflow nodes.

    Each node delegates to its subsystem when present in the node context and
    degrades gracefully otherwise.
    """
    return {
        "load_context": WorkflowNode(name="load_context", description="Load task context", handler=_load_context),
        "retrieve_memory": WorkflowNode(name="retrieve_memory", description="Retrieve relevant memories", handler=_retrieve_memory),
        "plan": WorkflowNode(name="plan", description="Create execution plan", handler=_plan_node),
        "execute_step": WorkflowNode(name="execute_step", description="Execute a plan step", handler=_execute_step),
        "critic": WorkflowNode(name="critic", description="Evaluate execution result", handler=_critic_node),
        "memory_write": WorkflowNode(name="memory_write", description="Write memories after run", handler=_memory_write),
        "finish": WorkflowNode(name="finish", description="Finish the workflow", handler=_finish_node),
    }
