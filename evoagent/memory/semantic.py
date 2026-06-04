"""SemanticMemory — long-term factual knowledge."""

from evoagent.memory.schema import MemoryItem, MemoryType


class SemanticMemory:
    """Utility for creating semantic (factual) memories."""

    @staticmethod
    def from_fact(concept: str, content: str, confidence: float = 0.7) -> MemoryItem:
        return MemoryItem(
            memory_type=MemoryType.SEMANTIC,
            content=f"{concept}: {content}",
            metadata={"concept": concept},
            confidence=confidence,
        )
