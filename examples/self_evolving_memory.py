"""Self-evolving memory example — learn from failures."""

import asyncio
import tempfile
from pathlib import Path

from evoagent.core.state import RunStatus, RuntimeState
from evoagent.memory.consolidation import MemoryConsolidator
from evoagent.memory.evolution import MemoryEvolution
from evoagent.memory.retriever import MemoryRetriever
from evoagent.memory.sqlite_store import SQLiteMemoryStore
from evoagent.memory.writer import MemoryWriter


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "memory.sqlite"
        store = SQLiteMemoryStore(db_path)

        # Simulate a failed run
        state = RuntimeState(run_id="run_fail_1", task="Delete temporary files", status=RunStatus.FAILED)
        state.add_error("Permission denied: cannot delete /tmp/protected")
        state.add_error("Tool bash returned exit code 1")

        writer = MemoryWriter(store)
        written = writer.write_from_run(state, success=False)
        print(f"Written {len(written)} memories from failed run:")
        for w in written:
            print(f"  [{w.memory_type.value}] {w.content[:100]}")

        # Now simulate a similar task — should retrieve the reflection
        retriever = MemoryRetriever(store)
        results = retriever.retrieve("delete files permission denied")
        print(f"\nRetrieved {len(results)} memories for similar query:")
        for r in results:
            print(f"  [{r.memory_type.value}] {r.content[:100]}")

        # Consolidate
        consolidator = MemoryConsolidator(store)
        merges = consolidator.consolidate()
        print(f"\nConsolidation: {merges} merges performed")

        # Evolve
        evolver = MemoryEvolution(store)
        updated = evolver.evolve_memories(recent_failures=["permission denied"])
        print(f"Evolution: {len(updated)} memories updated")

        store.close()


if __name__ == "__main__":
    asyncio.run(main())
