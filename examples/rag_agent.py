"""RAG agent example — ingest docs and answer questions."""

import asyncio
import tempfile
from pathlib import Path

from evoagent.rag.query_engine import QueryEngine


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Create test documents
        (root / "architecture.md").write_text("""
# EvoAgent Architecture
EvoAgent is a model-agnostic agent framework.
It supports DeepSeek, OpenAI, and LiteLLM backends.
The tool system provides file I/O, shell, python, and git tools.
        """)
        (root / "config.md").write_text("""
# Configuration
Set API keys via environment variables: DEEPSEEK_API_KEY.
Default model is deepseek-chat for execution, deepseek-reasoner for planning.
Config is loaded from evoagent.yaml with environment variable overrides.
        """)

        # Ingest
        qe = QueryEngine(chunk_size=200, chunk_overlap=50)
        count = qe.ingest_path(root)
        print(f"Ingested {count} chunks from {root}")

        # Query
        ctx = qe.build_context("What model does EvoAgent use for planning?", top_k=3)
        print(f"\nRetrieved context:\n{ctx}")


if __name__ == "__main__":
    asyncio.run(main())
