"""MemoryRetriever — search and format memories for prompt injection."""

from evoagent.core.time import utc_now_iso
from evoagent.memory.base import BaseMemoryStore
from evoagent.memory.schema import MemoryItem, MemoryType


class MemoryRetriever:
    """Retrieves relevant memories and formats them for LLM context.

    Supports:
    - Keyword search with importance weighting
    - Memory type filtering
    - last_used_at update on retrieval
    """

    def __init__(self, store: BaseMemoryStore, top_k: int = 5):
        self.store = store
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        context: str = "",
        memory_types: list[MemoryType] | None = None,
        top_k: int | None = None,
    ) -> list[MemoryItem]:
        """Retrieve relevant memories.

        Args:
            query: Search query.
            context: Additional context to refine search.
            memory_types: Optional filter by type.
            top_k: Override default top_k.

        Returns:
            Ranked list of MemoryItems.
        """
        combined = f"{query} {context}"
        results = self.store.search(combined, memory_types=memory_types, top_k=top_k or self.top_k)

        # Update last_used_at
        for item in results:
            try:
                self.store.update(item.id, last_used_at=utc_now_iso())
            except (KeyError, Exception):
                pass

        return results

    def format_for_prompt(self, memories: list[MemoryItem]) -> str:
        """Format memories into a text block for prompt injection.

        Args:
            memories: Retrieved MemoryItems.

        Returns:
            Formatted text block.
        """
        if not memories:
            return ""
        lines = ["## Relevant Memories"]
        for i, m in enumerate(memories, 1):
            type_label = m.memory_type.value.upper()
            lines.append(f"{i}. [{type_label}] {m.content}")
        return "\n".join(lines)
