# RAG / Knowledge Base

## Overview

EvoAgent's RAG module provides document loading, chunking, indexing, retrieval, and citation for augmenting Agent prompts with external knowledge.

## Pipeline

```
Document → Loader → Chunker → Index → Retriever → QueryEngine → Agent Prompt
```

## Document / Chunk Schema

- **Document**: `id`, `text`, `metadata`, `source`, `created_at`
- **DocumentChunk**: `id`, `document_id`, `text`, `start_char`, `end_char`, `metadata`, `score`

## Loaders

- `TextLoader`: loads a single text file (txt/md/py/json/yaml/...)
- `DirectoryLoader`: recursively loads all text files, skipping `.git`, `__pycache__`, `.venv`, `node_modules`

## Chunker

`SimpleTextChunker` splits by character count with overlap:
```python
chunker = SimpleTextChunker(chunk_size=1000, chunk_overlap=100)
chunks = chunker.chunk_document(doc)
```

## Retriever

- `KeywordRetriever`: token overlap scoring (mini BM25)
- `BaseRetriever`: abstract interface for future vector retrievers

## QueryEngine

End-to-end pipeline:

```python
qe = QueryEngine()
qe.ingest_path("/path/to/docs")
context = qe.build_context("question?", top_k=5)
# Returns formatted text for Agent prompt injection
```

## Citations

```python
builder = CitationBuilder()
label = builder.format_citation(chunk)
# "[doc.md: C100-C200]"
```

## Keyword Retrieval Limitations

- No semantic understanding — "car" won't match "automobile"
- No term importance weighting (pure TF)
- Scales poorly beyond ~50k chunks

## Future Integration

- **FAISS / Qdrant**: replace KeywordIndex with vector DB
- **Embedding models**: add semantic search
- **LLMReranker**: re-rank with LLM for better precision

## Agent Integration

Set `rag.enabled: true` in config and add paths to `rag.paths`. The Agent will:
1. Ingest documents on startup
2. Retrieve relevant chunks before each run
3. Inject into `AgentContext.retrieved_documents`
