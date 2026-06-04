"""SQLiteMemoryStore — persistent memory storage using sqlite3."""

import json
import sqlite3
from pathlib import Path

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso
from evoagent.memory.base import BaseMemoryStore
from evoagent.memory.schema import MemoryItem, MemoryType


class SQLiteMemoryStore(BaseMemoryStore):
    """SQLite-backed memory store with keyword search.

    Creates a table with columns matching MemoryItem fields.
    Metadata is stored as JSON text.
    """

    def __init__(self, db_path: str | Path = ".evoagent/memory.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                importance REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                source_run_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_used_at TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    def _row_to_item(self, row: sqlite3.Row) -> MemoryItem:
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata", "{}"))
        return MemoryItem(**d)

    def add(self, memory: MemoryItem) -> MemoryItem:
        if not memory.id:
            memory.id = generate_id("mem")
        now = utc_now_iso()
        memory.created_at = memory.created_at or now
        memory.updated_at = now
        self._conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, memory_type, content, metadata, importance, confidence,
                source_run_id, created_at, updated_at, last_used_at,
                success_count, failure_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                memory.id, memory.memory_type.value, memory.content,
                json.dumps(memory.metadata, ensure_ascii=False),
                memory.importance, memory.confidence, memory.source_run_id,
                memory.created_at, memory.updated_at, memory.last_used_at,
                memory.success_count, memory.failure_count,
            ),
        )
        self._conn.commit()
        return memory

    def get(self, memory_id: str) -> MemoryItem | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return self._row_to_item(row) if row else None

    def search(
        self, query: str, memory_types: list[MemoryType] | None = None, top_k: int = 5
    ) -> list[MemoryItem]:
        # Simple keyword matching: split query into words, match any
        words = query.lower().split()
        rows = self._conn.execute("SELECT * FROM memories").fetchall()
        scored: list[tuple[float, MemoryItem]] = []
        for row in rows:
            item = self._row_to_item(row)
            if memory_types and item.memory_type not in memory_types:
                continue
            score = 0.0
            content_lower = item.content.lower()
            for w in words:
                if w in content_lower:
                    score += 1.0
            # Boost by importance
            score *= (0.5 + item.importance)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def update(self, memory_id: str, **fields) -> MemoryItem:
        item = self.get(memory_id)
        if not item:
            raise KeyError(f"Memory not found: {memory_id}")
        for k, v in fields.items():
            if hasattr(item, k):
                setattr(item, k, v)
        item.updated_at = utc_now_iso()
        self.add(item)  # INSERT OR REPLACE
        return item

    def delete(self, memory_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def list(
        self, memory_type: MemoryType | None = None, limit: int = 100
    ) -> list[MemoryItem]:
        if memory_type:
            rows = self._conn.execute(
                "SELECT * FROM memories WHERE memory_type = ? ORDER BY updated_at DESC LIMIT ?",
                (memory_type.value, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
