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
        self, state: RuntimeState, context: dict[str, Any] | None = None
    ) -> RuntimeState:
        """Run the graph from entrypoint to finish.

        Args:
            state: Initial RuntimeState.
            context: Optional context dict passed to node handlers.

        Returns:
            Final RuntimeState.
        """
        self.graph.validate()
        ctx = context or {}
        current = self.graph.entrypoint
        if not current:
            state.add_error("Graph has no entrypoint.")
            return state

        state.status = RunStatus.RUNNING
        steps = 0

        while current is not None and steps < self.max_steps:
            steps += 1

            # Check for human interrupt
            if state.status == RunStatus.WAITING_FOR_HUMAN:
                break

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

            # Save checkpoint
            if self.save_checkpoints and self.checkpoint_manager:
                self.checkpoint_manager.save_checkpoint(
                    state, name=f"node_{current}"
                )

            # Check finish
            if self.graph.is_finish(current):
                state.status = RunStatus.SUCCEEDED
                break

            # Get next node
            current = self.graph.get_next_node(current, state)

        if steps >= self.max_steps:
            state.add_error(f"Max steps ({self.max_steps}) reached.")

        state.touch()
        if self.trace_recorder:
            self.trace_recorder.save_state(state)
        return state

    async def resume(
        self, run_id: str, checkpoint_id: str | None = None
    ) -> RuntimeState | None:
        """Resume from a saved checkpoint.

        Args:
            run_id: The run ID to resume.
            checkpoint_id: Specific checkpoint ID, or latest if None.

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
        return state
