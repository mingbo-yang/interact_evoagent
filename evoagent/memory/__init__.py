"""Memory system — working, episodic, semantic, procedural, reflection.

Provides:
- BaseMemoryStore: abstract interface
- SQLiteMemoryStore: persistent SQLite backend
- MemoryRetriever: search and format memories
- MemoryWriter: extract memories from execution results
- MemoryConsolidator: merge duplicates, update stats
- MemoryEvolution: evolve memories from recent traces
- WorkingMemory: short-term task context
- EpisodicMemory / SemanticMemory / ProceduralMemory / ReflectionMemory

Import sub-modules directly to avoid circular imports with core.
"""
