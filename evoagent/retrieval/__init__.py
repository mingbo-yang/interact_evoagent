"""Retrieval module — keyword, vector, and hybrid retrieval.

Provides:
- BaseRetriever: abstract interface
- BaseEmbeddingModel: text embedding interface
- MockEmbeddingModel: deterministic hash-based embedding for testing
- KeywordRetriever: inverted-index keyword search
- SimpleVectorIndex: cosine-similarity vector store
- HybridRetriever: combined keyword + vector search
- merge_scores: score merging utility
"""

from evoagent.retrieval.base import BaseRetriever  # noqa: F401
from evoagent.retrieval.embeddings import BaseEmbeddingModel, MockEmbeddingModel  # noqa: F401
from evoagent.retrieval.hybrid import HybridRetriever  # noqa: F401
from evoagent.retrieval.keyword import KeywordRetriever  # noqa: F401
from evoagent.retrieval.scoring import merge_scores  # noqa: F401
from evoagent.retrieval.vector import SimpleVectorIndex  # noqa: F401
