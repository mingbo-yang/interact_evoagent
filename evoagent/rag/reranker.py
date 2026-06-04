"""Reranker — reorder retrieval results by relevance."""

from evoagent.rag.document import DocumentChunk


class Reranker:
    """Simple score-based reranker.

    Future: LLMReranker that uses an LLM to re-score chunks.
    """

    def rerank(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Sort chunks by score descending."""
        return sorted(chunks, key=lambda c: c.score or 0.0, reverse=True)
