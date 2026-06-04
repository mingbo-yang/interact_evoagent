"""RAG — document loading, chunking, retrieval, citation.

Provides:
- Document / DocumentChunk schemas
- TextLoader / DirectoryLoader
- SimpleTextChunker
- KeywordIndex / KeywordRetriever
- Reranker
- QueryEngine: full ingest → retrieve → format pipeline
- CitationBuilder
"""

from evoagent.rag.chunker import SimpleTextChunker  # noqa: F401
from evoagent.rag.citations import CitationBuilder  # noqa: F401
from evoagent.rag.document import Document, DocumentChunk  # noqa: F401
from evoagent.rag.index import KeywordIndex  # noqa: F401
from evoagent.rag.loaders import DirectoryLoader, TextLoader  # noqa: F401
from evoagent.rag.query_engine import QueryEngine  # noqa: F401
from evoagent.rag.reranker import Reranker  # noqa: F401
from evoagent.rag.retriever import BaseRetriever, KeywordRetriever  # noqa: F401
