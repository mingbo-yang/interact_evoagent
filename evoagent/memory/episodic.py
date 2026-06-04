"""EpisodicMemory — records of past task executions."""

from evoagent.memory.schema import MemoryItem, MemoryType


class EpisodicMemory:
    """Utility for creating episodic memories from task executions.

    An episodic memory captures: task, action, observation, outcome.
    """

    @staticmethod
    def from_run(
        task: str,
        outcome: str,
        steps: int,
        success: bool,
        source_run_id: str,
        importance: float = 0.5,
    ) -> MemoryItem:
        return MemoryItem(
            memory_type=MemoryType.EPISODIC,
            content=f"Task: {task}\nOutcome: {outcome}\nSteps: {steps}",
            metadata={
                "task": task,
                "outcome": outcome,
                "steps": steps,
                "success": success,
            },
            source_run_id=source_run_id,
            importance=importance,
            success_count=1 if success else 0,
            failure_count=0 if success else 1,
        )
