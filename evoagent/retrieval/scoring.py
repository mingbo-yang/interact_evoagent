"""Scoring utilities for hybrid retrieval."""

from evoagent.retrieval.base import BaseRetriever


def keyword_score(retriever: BaseRetriever, query: str, item_id: str) -> float:
    """Get the keyword score for an item."""
    results = retriever.search(query, top_k=100)
    for r in results:
        if r["id"] == item_id:
            return r.get("score", 0.0)
    return 0.0


def merge_scores(keyword_results: list[dict], vector_results: list[dict],
                 alpha: float = 0.5) -> list[dict]:
    """Merge keyword and vector results with weighted scoring.

    final = alpha * keyword_score + (1 - alpha) * vector_score
    """
    scores: dict[str, dict] = {}
    max_kw = max((r.get("score", 0) for r in keyword_results), default=1.0)
    max_vec = max((r.get("score", 0) for r in vector_results), default=1.0)

    for r in keyword_results:
        rid = r["id"]
        kw = r.get("score", 0) / max(max_kw, 1e-9)
        scores[rid] = {"id": rid, "text": r.get("text", ""), "kw": kw, "vec": 0.0}

    for r in vector_results:
        rid = r["id"]
        vec = r.get("score", 0) / max(max_vec, 1e-9)
        if rid in scores:
            scores[rid]["vec"] = vec
        else:
            scores[rid] = {"id": rid, "text": r.get("text", ""), "kw": 0.0, "vec": vec}

    merged = []
    for rid, s in scores.items():
        final = alpha * s["kw"] + (1 - alpha) * s["vec"]
        merged.append({"id": rid, "text": s["text"], "score": final})
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged
