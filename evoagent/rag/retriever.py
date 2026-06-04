"""Retriever — BaseRetriever ABC and KeywordRetriever implementation."""

from abc import ABC, abstractmethod

from evoagent.rag.document import DocumentChunk
from evoagent.rag.index import KeywordIndex


class BaseRetriever(ABC):
    """Abstract retriever interface."""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5, **filters) -> list[DocumentChunk]:
        ...


class KeywordRetriever(BaseRetriever):
    """Keyword-based retriever backed by KeywordIndex."""

    def __init__(self, index: KeywordIndex | None = None):
        self.index = index or KeywordIndex()

    def retrieve(self, query: str, top_k: int = 5, **filters) -> list[DocumentChunk]:
        return self.index.search(query, top_k=top_k)
