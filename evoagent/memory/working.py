"""WorkingMemory — short-term task context (lightweight, non-persistent by default)."""

from evoagent.memory.schema import MemoryItem, MemoryType


class WorkingMemory:
    """In-memory store for the current task's short-term context.

    Typically holds < 20 items, cleared after each run.
    Not persisted to SQLite by default — keeps the store clean.
    """

    def __init__(self, max_items: int = 20):
        self.max_items = max_items
        self._items: list[MemoryItem] = []

    def add(self, content: str, metadata: dict | None = None) -> MemoryItem:
        item = MemoryItem(memory_type=MemoryType.WORKING, content=content, metadata=metadata or {})
        self._items.append(item)
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items:]
        return item

    def get_all(self) -> list[MemoryItem]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
