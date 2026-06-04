"""HybridRetriever — combine keyword + vector search."""

from evoagent.retrieval.base import BaseRetriever
from evoagent.retrieval.embeddings import BaseEmbeddingModel
from evoagent.retrieval.keyword import KeywordRetriever
from evoagent.retrieval.scoring import merge_scores
from evoagent.retrieval.vector import SimpleVectorIndex


class HybridRetriever(BaseRetriever):
    """Combined keyword + vector retrieval with configurable weighting.

    final_score = alpha * keyword_score + (1 - alpha) * vector_score

    Usage:
        kw = KeywordRetriever()
        vec = SimpleVectorIndex()
        emb = MockEmbeddingModel()
        hybrid = HybridRetriever(kw, vec, emb, alpha=0.5)
        hybrid.add_items([...])
        results = hybrid.search("query", top_k=5)
    """

    def __init__(self, keyword: KeywordRetriever, vector: SimpleVectorIndex,
                 embedding: BaseEmbeddingModel, alpha: float = 0.5):
        self.keyword = keyword
        self.vector = vector
        self.embedding = embedding
        self.alpha = alpha

    def add_items(self, items: list[dict]) -> None:
        # Add to keyword index
        kw_items = [{"id": it["id"], "text": it.get("text", "")} for it in items]
        self.keyword.add_items(kw_items)
        # Embed and add to vector index
        texts = [it.get("text", "") for it in items]
        vectors = self.embedding.embed_texts(texts)
        vec_items = [{"id": it["id"], "text": it.get("text", ""), "vector": v}
                     for it, v in zip(items, vectors, strict=True)]
        self.vector.add_items(vec_items)

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        kw_results = self.keyword.search(query, top_k=max(top_k * 2, 20))
        query_vec = self.embedding.embed_text(query)
        vec_results = self.vector.search_by_vector(query_vec, top_k=max(top_k * 2, 20))
        merged = merge_scores(kw_results, vec_results, alpha=self.alpha)
        return merged[:top_k]

    def clear(self) -> None:
        self.keyword.clear()
        self.vector.clear()
