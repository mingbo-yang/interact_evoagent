"""WorkflowRuntime — execute a WorkflowGraph step by step."""

from typing import Any

from evoagent.core.state import RunStatus, RuntimeState
from evoagent.logging.checkpoint import CheckpointManager
from evoagent.logging.event import EventType
from evoagent.logging.trace import TraceRecorder
from evoagent.workflow.graph import WorkflowGraph


class WorkflowRuntime:
    """Execute a WorkflowGraph from entry to finish.

    Features:
    - Step-by-step execution
    - Checkpoint after each node
    - Max steps limit
    - Human interrupt (waiting_for_human status)
    - Error capture into state.errors
    - Event logging via TraceRecorder

    Usage:
        runtime = WorkflowRuntime(graph, trace_recorder=recorder)
        final_state = await runtime.run(initial_state)
    """

    def __init__(
        self,
        graph: WorkflowGraph,
        checkpoint_manager: CheckpointManager | None = None,
        trace_recorder: TraceRecorder | None = None,
        max_steps: int = 50,
        save_checkpoints: bool = True,
    ):
        self.graph = graph
        self.checkpoint_manager = checkpoint_manager
        self.trace_recorder = trace_recorder
        self.max_steps = max_steps
        self.save_checkpoints = save_checkpoints

    async def run(
        self, state: RuntimeState, context: dict[str, Any] | None = None,
        start_node: str | None = None,
    ) -> RuntimeState:
        """Run the graph to finish, interrupt, or dead-end.

        Resumable: the next node to execute is persisted in
        ``state.metadata['workflow_current_node']`` and saved with each
        checkpoint. If ``start_node`` is omitted, execution continues from that
        saved marker (set by a prior interrupted run) or the graph entrypoint.

        Args:
            state: Initial (or resumed) RuntimeState.
            context: Optional context dict passed to node handlers.
            start_node: Explicit node to start from (overrides the marker).

        Returns:
            Final RuntimeState.
        """
        self.graph.validate()
        ctx = context or {}
        current = (
            start_node
            or state.metadata.get("workflow_current_node")
            or self.graph.entrypoint
        )
        if not current:
            state.add_error("Graph has no entrypoint.")
            return state

        state.status = RunStatus.RUNNING
        steps = 0
        hit_limit = False

        while current is not None:
            if steps >= self.max_steps:
                hit_limit = True
                break
            steps += 1

            # Execute node
            node = self.graph.get_node(current)
            if self.trace_recorder:
                self.trace_recorder.log(
                    EventType.TOOL_CALL_STARTED,
                    payload={"node": current},
                    step_id=str(steps),
                )

            try:
                state = await node.execute(state, ctx)
            except Exception as e:
                state.add_error(f"Node '{current}' failed: {e}")

            if self.trace_recorder:
                self.trace_recorder.log(
                    EventType.TOOL_CALL_FINISHED,
                    payload={"node": current},
                    step_id=str(steps),
                )

            # Finish node: terminal success.
            if self.graph.is_finish(current):
                state.status = RunStatus.SUCCEEDED
                state.metadata.pop("workflow_current_node", None)
                self._maybe_checkpoint(state, current)
                break

            # Human interrupt: stop, remember the node to resume at.
            if state.status == RunStatus.WAITING_FOR_HUMAN:
                state.metadata["workflow_current_node"] = self.graph.get_next_node(current, state)
                self._maybe_checkpoint(state, current)
                break

            nxt = self.graph.get_next_node(current, state)
            if nxt is None:
                # Dead end: no matching outgoing edge and not a finish node.
                state.add_error(f"Node '{current}' has no matching outgoing edge.")
                if state.status == RunStatus.RUNNING:
                    state.status = RunStatus.FAILED
                state.metadata.pop("workflow_current_node", None)
                self._maybe_checkpoint(state, current)
                break

            # Persist the resume point (next node) before checkpointing.
            state.metadata["workflow_current_node"] = nxt
            self._maybe_checkpoint(state, current)
            current = nxt

        if hit_limit:
            state.add_error(f"Max steps ({self.max_steps}) reached.")
            if state.status == RunStatus.RUNNING:
                state.status = RunStatus.FAILED

        state.touch()
        if self.trace_recorder:
            self.trace_recorder.save_state(state)
        return state

    def _maybe_checkpoint(self, state: RuntimeState, node_name: str) -> None:
        if self.save_checkpoints and self.checkpoint_manager:
            self.checkpoint_manager.save_checkpoint(state, name=f"node_{node_name}")

    async def resume(
        self, run_id: str, checkpoint_id: str | None = None,
        context: dict[str, Any] | None = None, continue_run: bool = False,
    ) -> RuntimeState | None:
        """Resume from a saved checkpoint.

        Loads the checkpointed state (which carries the saved resume node in
        ``metadata['workflow_current_node']``). By default it only loads and
        returns the state with status RUNNING; pass ``continue_run=True`` to
        re-enter execution from the saved node rather than the entrypoint.

        Args:
            run_id: The run ID to resume.
            checkpoint_id: Specific checkpoint ID, or latest if None.
            context: Context dict for node handlers (used when continuing).
            continue_run: If True, continue executing the graph.

        Returns:
            Resumed RuntimeState, or None if checkpoint not found.
        """
        if not self.checkpoint_manager:
            return None
        chk = self.checkpoint_manager.load_checkpoint(run_id, checkpoint_id)
        if chk is None or chk.state is None:
            return None
        state = chk.state
        state.status = RunStatus.RUNNING
        if continue_run:
            return await self.run(state, context=context)
        return state
