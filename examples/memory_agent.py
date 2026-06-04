"""Memory agent example — add, retrieve, and use memories."""

import asyncio
import tempfile
from pathlib import Path

from evoagent.memory.retriever import MemoryRetriever
from evoagent.memory.schema import MemoryItem, MemoryType
from evoagent.memory.sqlite_store import SQLiteMemoryStore


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "memory.sqlite"
        store = SQLiteMemoryStore(db_path)
        retriever = MemoryRetriever(store)

        # Add some memories
        store.add(MemoryItem(
            memory_type=MemoryType.SEMANTIC,
            content="EvoAgent is a Python agent framework that uses DeepSeek.",
            importance=0.8,
            confidence=0.9,
        ))
        store.add(MemoryItem(
            memory_type=MemoryType.PROCEDURAL,
            content="When asked to list files, use the list_directory tool.",
            success_count=3,
        ))
        store.add(MemoryItem(
            memory_type=MemoryType.EPISODIC,
            content="Task: Read config file. Outcome: Success. Steps: 2.",
            source_run_id="run_123",
            success_count=1,
        ))

        # Retrieve
        results = retriever.retrieve("list files")
        print(f"Found {len(results)} memories for 'list files':")
        for r in results:
            print(f"  [{r.memory_type.value}] {r.content[:80]}")

        # Format for prompt
        formatted = retriever.format_for_prompt(results)
        print(f"\nPrompt injection:\n{formatted}")

        store.close()


if __name__ == "__main__":
    asyncio.run(main())
