"""KeywordRetriever with inverted index for efficient text search."""

import re
from collections import defaultdict

from evoagent.retrieval.base import BaseRetriever


class KeywordRetriever(BaseRetriever):
    """Inverted-index keyword retriever.

    Replaces the old O(n) scan with an inverted index for
    efficient multi-word queries. Falls back gracefully for
    small datasets.
    """

    def __init__(self):
        self._items: dict[str, dict] = {}
        self._index: dict[str, set[str]] = defaultdict(set)

    def add_items(self, items: list[dict]) -> None:
        for item in items:
            item_id = item["id"]
            text = item.get("text", "")
            self._items[item_id] = item
            tokens = self._tokenize(text)
            for t in set(tokens):
                self._index[t].add(item_id)

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        if not query:
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}
        for token in set(query_tokens):
            tf = query_tokens.count(token)
            for item_id in self._index.get(token, set()):
                scores[item_id] = scores.get(item_id, 0.0) + tf

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for item_id, score in ranked[:top_k]:
            item = self._items.get(item_id)
            if item:
                results.append({"id": item_id, "text": item.get("text", ""), "score": score})
        return results

    def clear(self) -> None:
        self._items.clear()
        self._index.clear()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())
