"""QueryEngine — ingest documents and retrieve context for Agent prompts."""

from pathlib import Path

from evoagent.rag.chunker import SimpleTextChunker
from evoagent.rag.document import DocumentChunk
from evoagent.rag.loaders import DirectoryLoader, TextLoader
from evoagent.rag.reranker import Reranker
from evoagent.rag.retriever import KeywordRetriever


class QueryEngine:
    """End-to-end RAG pipeline: load → chunk → index → retrieve → format.

    Usage:
        qe = QueryEngine()
        qe.ingest_path("/path/to/docs")
        ctx = qe.build_context("What is EvoAgent?", top_k=3)
        # ctx can be injected into Agent prompt
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        top_k: int = 5,
    ):
        self.chunker = SimpleTextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.retriever = KeywordRetriever()
        self.reranker = Reranker()
        self.top_k = top_k

    def ingest_path(self, path: str | Path) -> int:
        """Load and index all documents under a path.

        Args:
            path: File or directory path.

        Returns:
            Number of chunks ingested.
        """
        p = Path(path)
        if p.is_file():
            loader = TextLoader()
            doc = loader.load(p)
            docs = [doc] if doc else []
        else:
            loader = DirectoryLoader()
            docs = loader.load(p)

        all_chunks: list[DocumentChunk] = []
        for doc in docs:
            chunks = self.chunker.chunk_document(doc)
            all_chunks.extend(chunks)

        self.retriever.index.add_documents(all_chunks)
        return len(all_chunks)

    def retrieve(self, query: str, top_k: int | None = None) -> list[DocumentChunk]:
        """Retrieve relevant chunks."""
        chunks = self.retriever.retrieve(query, top_k=top_k or self.top_k)
        return self.reranker.rerank(chunks)

    def build_context(self, query: str, top_k: int | None = None) -> str:
        """Retrieve and format document context for Agent prompt injection.

        Args:
            query: The task or question.
            top_k: Override default top_k.

        Returns:
            Formatted text block of retrieved document snippets.
        """
        chunks = self.retrieve(query, top_k=top_k)
        if not chunks:
            return ""
        lines = ["## Retrieved Documents"]
        for i, c in enumerate(chunks, 1):
            source = c.metadata.get("source", c.document_id)
            lines.append(f"### Doc {i} [{source}]")
            lines.append(c.text[:500])
            lines.append("")
        return "\n".join(lines)
