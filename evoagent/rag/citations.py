"""CitationBuilder — generate citation labels for retrieved chunks."""

from evoagent.rag.document import DocumentChunk


class CitationBuilder:
    """Generate citation labels for chunks and format them.

    Usage:
        builder = CitationBuilder()
        label = builder.format_citation(chunk)  # "[doc_abc: L100-L150]"
    """

    @staticmethod
    def format_citation(chunk: DocumentChunk) -> str:
        """Generate a citation label for a chunk.

        Args:
            chunk: A retrieved DocumentChunk.

        Returns:
            Citation string like "[source_file: L100-L200]".
        """
        source = chunk.metadata.get("source", chunk.document_id or "unknown")
        return f"[{source}: C{chunk.start_char}-C{chunk.end_char}]"

    @staticmethod
    def format_block(chunks: list[DocumentChunk]) -> str:
        """Format multiple chunks with citations."""
        if not chunks:
            return ""
        lines = ["## Sources"]
        for i, c in enumerate(chunks, 1):
            label = CitationBuilder.format_citation(c)
            lines.append(f"{i}. {label}")
            lines.append(f"   {c.text[:120]}...")
        return "\n".join(lines)
