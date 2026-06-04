# Memory System

## Why layered memory?

Single-layer memory (just chat history) has limitations:
- Can't distinguish facts from procedures
- Can't learn from failures
- Can't self-improve over time

EvoAgent's 5-layer memory addresses this:

| Layer | Purpose | Lifespan | Example |
|-------|---------|----------|---------|
| **Working** | Current task context | One run | "User asked for a Python script" |
| **Episodic** | Past run experiences | Persistent | "Successfully created requirements.txt in 3 steps" |
| **Semantic** | Factual knowledge | Persistent | "DeepSeek API base URL is https://api.deepseek.com/v1" |
| **Procedural** | How-to / skills | Persistent | "When asked to list files, use list_directory tool" |
| **Reflection** | Failure analysis | Persistent | "rm -rf failed: use explicit paths with bash tool" |

## MemoryItem Schema

All layers use the same `MemoryItem` schema with `memory_type` discriminator:

- `id`, `memory_type`, `content`
- `importance` (0-1), `confidence` (0-1)
- `source_run_id` — traceability
- `success_count`, `failure_count` — usage stats
- `metadata` — type-specific data (task, trigger, failure_pattern, etc.)

## SQLiteMemoryStore

Persistent storage using sqlite3 (zero dependencies beyond stdlib):

```python
store = SQLiteMemoryStore(".evoagent/memory.sqlite")
store.add(memory)
store.search("query", top_k=5)
store.update(memory_id, importance=0.9)
store.delete(memory_id)
```

## MemoryRetriever

Searches and formats for prompt injection:

```python
retriever = MemoryRetriever(store)
memories = retriever.retrieve("current task description")
formatted = retriever.format_for_prompt(memories)
# Returns "## Relevant Memories\n1. [EPISODIC] ..."
```

## MemoryWriter

Extracts memories from `RuntimeState` after execution:
- Successful run → episodic memory
- Failed run → episodic + reflection memory

## MemoryConsolidator

Periodic maintenance:
- Merges similar memories (Jaccard word similarity)
- Updates success/failure counts
- Adjusts importance and confidence

## MemoryEvolution

Adapts memories based on recent experiences:
- Boosts importance of memories matching successful patterns
- Decreases confidence of memories matching failure patterns

## Self-evolving Memory Research Directions

1. **LLM-based consolidation**: Use LLM to summarize and merge memories
2. **Embedding-based similarity**: Replace keyword search with vector embeddings
3. **Automatic skill extraction**: Extract procedural memories from repeated successful patterns
4. **Forgetting curve**: Implement Ebbinghaus-style importance decay

## Avoiding Memory Pollution

- `importance` floor: low-importance memories can be pruned
- `confidence` threshold: memories below 0.2 can be auto-deleted
- `source_run_id` enables bulk cleanup of bad runs
- Consolidator merges duplicates to prevent bloat
