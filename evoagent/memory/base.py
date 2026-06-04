"""BaseMemoryStore — abstract interface for memory storage."""

from abc import ABC, abstractmethod

from evoagent.memory.schema import MemoryItem, MemoryType


class BaseMemoryStore(ABC):
    """Abstract store for MemoryItem persistence.

    All memory backends (SQLite, vector DB, etc.) implement this.
    """

    @abstractmethod
    def add(self, memory: MemoryItem) -> MemoryItem:
        """Add a memory and return it with assigned ID."""
        ...

    @abstractmethod
    def get(self, memory_id: str) -> MemoryItem | None:
        """Get a memory by ID."""
        ...

    @abstractmethod
    def search(
        self, query: str, memory_types: list[MemoryType] | None = None, top_k: int = 5
    ) -> list[MemoryItem]:
        """Search memories by keyword relevance.

        Args:
            query: Search query string.
            memory_types: Optional filter by memory type.
            top_k: Max results to return.

        Returns:
            Ranked list of MemoryItems.
        """
        ...

    @abstractmethod
    def update(self, memory_id: str, **fields) -> MemoryItem:
        """Update fields of an existing memory."""
        ...

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if deleted."""
        ...

    @abstractmethod
    def list(
        self, memory_type: MemoryType | None = None, limit: int = 100
    ) -> list[MemoryItem]:
        """List memories, optionally filtered by type."""
        ...
