"""MemoryConsolidator — merge duplicates, update stats, decay importance."""

from evoagent.memory.base import BaseMemoryStore
from evoagent.memory.schema import MemoryItem


class MemoryConsolidator:
    """Consolidates memories by merging duplicates and updating scores.

    Rule-based: no LLM required.
    - Merges highly similar memories
    - Updates success_count / failure_count
    - Adjusts importance based on usage
    """

    def __init__(self, store: BaseMemoryStore, similarity_threshold: float = 0.7):
        self.store = store
        self.similarity_threshold = similarity_threshold

    def consolidate(self) -> int:
        """Run consolidation on all memories.

        Returns:
            Number of merges performed.
        """
        merges = 0
        all_items = self.store.list(limit=1000)

        # Simple dedup: same memory_type + similar content
        for i, item in enumerate(all_items):
            for j in range(i + 1, len(all_items)):
                other = all_items[j]
                if item.memory_type != other.memory_type:
                    continue
                if self._similarity(item.content, other.content) >= self.similarity_threshold:
                    self._merge(item, other)
                    merges += 1
        return merges

    def _similarity(self, a: str, b: str) -> float:
        """Jaccard-like similarity on word sets."""
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _merge(self, keep: MemoryItem, discard: MemoryItem) -> None:
        keep.success_count += discard.success_count
        keep.failure_count += discard.failure_count
        keep.importance = min(1.0, max(keep.importance, discard.importance) + 0.05)
        keep.confidence = min(1.0, (keep.confidence + discard.confidence) / 2 + 0.05)
        self.store.update(keep.id,
                          success_count=keep.success_count,
                          failure_count=keep.failure_count,
                          importance=keep.importance,
                          confidence=keep.confidence)
        self.store.delete(discard.id)

    def update_stats(self, memory_id: str, success: bool) -> None:
        """Increment success or failure counter."""
        item = self.store.get(memory_id)
        if not item:
            return
        if success:
            item.success_count += 1
            item.importance = min(1.0, item.importance + 0.05)
        else:
            item.failure_count += 1
            item.importance = max(0.1, item.importance - 0.05)
        self.store.update(item.id,
                          success_count=item.success_count,
                          failure_count=item.failure_count,
                          importance=item.importance)
