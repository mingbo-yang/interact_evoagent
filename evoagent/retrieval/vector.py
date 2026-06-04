"""SimpleVectorIndex — pure Python cosine-similarity vector store."""

import math

from evoagent.retrieval.base import BaseRetriever


class SimpleVectorIndex(BaseRetriever):
    """In-memory vector index with cosine similarity.

    Stores (id, text, vector) tuples and searches by cosine distance.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim
        self._items: list[dict] = []

    def add_items(self, items: list[dict]) -> None:
        for item in items:
            if "vector" not in item:
                continue
            self._items.append({
                "id": item["id"],
                "text": item.get("text", ""),
                "vector": item["vector"],
            })

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        return []  # Overridden in subclasses that use embedding

    def search_by_vector(self, query_vec: list[float], top_k: int = 5) -> list[dict]:
        if not self._items:
            return []
        scored = []
        for item in self._items:
            sim = self._cosine(query_vec, item["vector"])
            scored.append((sim, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": it["id"], "text": it["text"], "score": s}
                for s, it in scored[:top_k]]

    def clear(self) -> None:
        self._items.clear()

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
