"""ReflectionMemory — failure analysis and fix strategies."""

from evoagent.memory.schema import MemoryItem, MemoryType


class ReflectionMemory:
    """Utility for creating reflection memories from failures."""

    @staticmethod
    def from_failure(
        failure_pattern: str,
        root_cause: str,
        fix_strategy: str,
        source_run_id: str,
        importance: float = 0.7,
    ) -> MemoryItem:
        return MemoryItem(
            memory_type=MemoryType.REFLECTION,
            content=f"Pattern: {failure_pattern}\nCause: {root_cause}\nFix: {fix_strategy}",
            metadata={
                "failure_pattern": failure_pattern,
                "root_cause": root_cause,
                "fix_strategy": fix_strategy,
            },
            source_run_id=source_run_id,
            importance=importance,
            confidence=0.6,
        )
