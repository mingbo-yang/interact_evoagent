"""KeywordIndex — simple token-overlap index for keyword retrieval."""

import re

from evoagent.rag.document import DocumentChunk


class KeywordIndex:
    """In-memory keyword index using token overlap scoring.

    Like a mini BM25 without IDF — scores by term frequency
    weighted by chunk length.
    """

    def __init__(self):
        self._chunks: list[DocumentChunk] = []
        self._term_index: dict[str, set[int]] = {}  # term → set of chunk indices

    def add_documents(self, chunks: list[DocumentChunk]) -> None:
        """Add chunks to the index."""
        for chunk in chunks:
            self._add_chunk(chunk)

    def _add_chunk(self, chunk: DocumentChunk) -> None:
        idx = len(self._chunks)
        self._chunks.append(chunk)
        tokens = self._tokenize(chunk.text)
        for token in set(tokens):
            self._term_index.setdefault(token, set()).add(idx)

    def search(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        """Search for chunks matching the query.

        Args:
            query: Search query.
            top_k: Max results.

        Returns:
            Ranked list of DocumentChunks with scores.
        """
        if not query or not self._chunks:
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # Score each chunk by term overlap
        scores: dict[int, float] = {}
        for term in set(query_terms):
            tf = query_terms.count(term)
            for idx in self._term_index.get(term, set()):
                chunk_tf = self._tokenize(self._chunks[idx].text).count(term)
                scores[idx] = scores.get(idx, 0.0) + tf * chunk_tf

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked[:top_k]:
            chunk = self._chunks[idx].model_copy()
            chunk.score = score
            results.append(chunk)
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase and split into alphanumeric tokens."""
        return re.findall(r"[a-zA-Z0-9]+", text.lower())
