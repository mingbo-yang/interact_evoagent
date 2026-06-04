"""Tests for retrieval module (MockEmbedding, SimpleVectorIndex, HybridRetriever, KeywordRetriever)."""


from evoagent.retrieval.embeddings import MockEmbeddingModel
from evoagent.retrieval.hybrid import HybridRetriever
from evoagent.retrieval.keyword import KeywordRetriever
from evoagent.retrieval.scoring import merge_scores
from evoagent.retrieval.vector import SimpleVectorIndex


def test_mock_embedding_deterministic():
    emb = MockEmbeddingModel()
    v1 = emb.embed_text("hello")
    v2 = emb.embed_text("hello")
    assert v1 == v2
    assert len(v1) == 64


def test_mock_embedding_different_texts():
    emb = MockEmbeddingModel()
    v1 = emb.embed_text("hello")
    v2 = emb.embed_text("world")
    assert v1 != v2


def test_mock_embed_texts():
    emb = MockEmbeddingModel()
    vecs = emb.embed_texts(["a", "b", "c"])
    assert len(vecs) == 3
    assert all(len(v) == 64 for v in vecs)


def test_hybrid_retriever():
    kw = KeywordRetriever()
    vec = SimpleVectorIndex(dim=64)
    emb = MockEmbeddingModel()
    hybrid = HybridRetriever(kw, vec, emb, alpha=0.5)

    items = [
        {"id": "1", "text": "Python agent framework"},
        {"id": "2", "text": "JavaScript frontend library"},
        {"id": "3", "text": "Deep learning with Python"},
    ]
    hybrid.add_items(items)
    results = hybrid.search("Python agent", top_k=2)
    assert len(results) >= 1
    assert all("id" in r and "score" in r for r in results)


def test_hybrid_clear():
    kw = KeywordRetriever()
    vec = SimpleVectorIndex()
    emb = MockEmbeddingModel()
    hybrid = HybridRetriever(kw, vec, emb)
    hybrid.add_items([{"id": "1", "text": "test"}])
    assert len(hybrid.search("test")) >= 1
    hybrid.clear()
    assert hybrid.search("test") == []


def test_merge_scores():
    kw = [{"id": "a", "score": 0.8}, {"id": "b", "score": 0.3}]
    vec = [{"id": "a", "score": 0.2}, {"id": "c", "score": 0.9}]
    merged = merge_scores(kw, vec, alpha=0.5)
    assert len(merged) == 3
    ids = {r["id"] for r in merged}
    assert ids == {"a", "b", "c"}


def test_keyword_retriever_inverted_index():
    kw = KeywordRetriever()
    kw.add_items([{"id": "1", "text": "hello world"}, {"id": "2", "text": "goodbye world"}])
    results = kw.search("hello")
    assert len(results) == 1
    assert results[0]["id"] == "1"
