"""Built-in workflow nodes wrapping Planner/Executor/Critic/Memory."""

from typing import Any

from evoagent.core.state import RuntimeState
from evoagent.workflow.node import WorkflowNode


async def _passthrough(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    return state


async def _load_context(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Load context from config or ctx dict."""
    system_prompt = ctx.get("system_prompt", "You are a helpful assistant.")
    state.metadata["system_prompt"] = system_prompt
    return state


async def _retrieve_memory(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Retrieve relevant memories (placeholder)."""
    # Phase 8 integration point
    return state


async def _plan_node(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Plan step (placeholder — delegate to Planner)."""
    state.metadata["plan_requested"] = True
    return state


async def _execute_step(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Execute a step (placeholder — delegate to Executor)."""
    state.metadata["step_executed"] = True
    return state


async def _critic_node(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Critic evaluation (placeholder)."""
    state.metadata["critic_done"] = True
    return state


async def _memory_write(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Write memories after run (placeholder)."""
    state.metadata["memory_written"] = True
    return state


async def _finish_node(state: RuntimeState, ctx: dict[str, Any]) -> RuntimeState:
    """Mark task as finished."""
    state.metadata["finished"] = True
    return state


def make_builtin_nodes() -> dict[str, WorkflowNode]:
    """Create a dict of built-in workflow nodes.

    These are lightweight placeholders that can be replaced
    with full Planner/Executor/Critic/MemoryWriter implementations.
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
