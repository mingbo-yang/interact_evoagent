"""MemoryWriter — extract memories from RuntimeState and traces."""

from evoagent.core.state import RuntimeState
from evoagent.memory.base import BaseMemoryStore
from evoagent.memory.episodic import EpisodicMemory
from evoagent.memory.reflection import ReflectionMemory
from evoagent.memory.schema import MemoryItem


class MemoryWriter:
    """Generates memory candidates from execution results.

    Rule-based: no LLM required.
    - Successful runs → episodic memory
    - Failed runs → reflection memory
    - Writes source_run_id for traceability
    """

    def __init__(self, store: BaseMemoryStore):
        self.store = store

    def write_from_run(self, state: RuntimeState, success: bool) -> list[MemoryItem]:
        """Extract and persist memories from a completed run.

        Args:
            state: The final RuntimeState.
            success: Whether the run succeeded.

        Returns:
            List of written MemoryItems.
        """
        written: list[MemoryItem] = []

        # Episodic memory
        outcome = "Success" if success else "Failed"
        steps = len(state.step_results)
        ep = EpisodicMemory.from_run(
            task=state.task,
            outcome=outcome,
            steps=steps,
            success=success,
            source_run_id=state.run_id,
            importance=0.6 if success else 0.8,
        )
        self.store.add(ep)
        written.append(ep)

        # Reflection memory on failure
        if not success and state.errors:
            error_text = "; ".join(state.errors[-3:])
            ref = ReflectionMemory.from_failure(
                failure_pattern=error_text[:200],
                root_cause="Step execution failed",
                fix_strategy="Review tool arguments and retry with corrected parameters.",
                source_run_id=state.run_id,
                importance=0.8,
            )
            self.store.add(ref)
            written.append(ref)

        return written
