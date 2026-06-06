"""SimpleTextChunker — split documents into overlapping chunks."""

from evoagent.rag.document import Document, DocumentChunk


class SimpleTextChunker:
    """Split text into fixed-size chunks with overlap.

    Preserves source metadata from the parent document.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"chunk_overlap must be >= 0, got {chunk_overlap}")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: Document) -> list[DocumentChunk]:
        """Split a single document into chunks."""
        return self.chunk_text(doc.text, doc.id, doc.metadata, doc.source)

    def chunk_text(
        self, text: str, document_id: str = "", metadata: dict | None = None,
        source: str = "",
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        if not text:
            return chunks
        meta = dict(metadata or {})
        meta["source"] = source

        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            # overlap >= size: still make progress to avoid an infinite loop.
            step = max(1, self.chunk_size)

        pos = 0
        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))
            chunk_text = text[pos:end]
            chunks.append(DocumentChunk(
                document_id=document_id,
                text=chunk_text,
                start_char=pos,
                end_char=end,
                metadata=meta,
            ))
            if end >= len(text):
                break
            pos += step
        return chunks
