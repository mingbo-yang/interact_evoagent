"""BaseRetriever — abstract interface for all retrievers."""

from abc import ABC, abstractmethod


class BaseRetriever(ABC):
    """Abstract retriever for document/memory/chunk search."""

    @abstractmethod
    def add_items(self, items: list[dict]) -> None:
        """Add items with at least 'id' and 'text' fields."""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        """Search and return list of {'id':..., 'text':..., 'score':...}."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all items."""
        ...
