"""MemoryEvolution — evolve memories based on recent traces and outcomes.

Rule-based first version. Future: LLM-powered evolution.
"""

from evoagent.memory.base import BaseMemoryStore
from evoagent.memory.schema import MemoryItem


class MemoryEvolution:
    """Evolves memories by analyzing recent successes and failures.

    First version uses simple rule-based heuristics.
    LLM-based evolution is reserved for future research.
    """

    def __init__(self, store: BaseMemoryStore,
                 success_boost: float = 0.1,
                 failure_penalty: float = 0.1):
        self.store = store
        self.success_boost = success_boost
        self.failure_penalty = failure_penalty

    def evolve_memories(
        self,
        recent_successes: list[str] | None = None,
        recent_failures: list[str] | None = None,
    ) -> list[MemoryItem]:
        """Evolve memories based on recent traces.

        Args:
            recent_successes: Descriptions of recent successful tasks.
            recent_failures: Descriptions of recent failed tasks.

        Returns:
            Updated memories.
        """
        updated: list[MemoryItem] = []

        # Boost memories matching successful patterns
        if recent_successes:
            for success in recent_successes:
                matches = self.store.search(success, top_k=3)
                for m in matches:
                    m.success_count += 1
                    m.importance = min(1.0, m.importance + 0.1)
                    self.store.update(m.id, success_count=m.success_count, importance=m.importance)
                    updated.append(m)

        # Adjust memories matching failure patterns
        if recent_failures:
            for failure in recent_failures:
                matches = self.store.search(failure, top_k=3)
                for m in matches:
                    m.failure_count += 1
                    m.confidence = max(0.1, m.confidence - 0.1)
                    self.store.update(m.id, failure_count=m.failure_count, confidence=m.confidence)
                    updated.append(m)

        return updated
