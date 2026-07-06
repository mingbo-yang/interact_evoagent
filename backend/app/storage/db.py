from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.schemas.workflow_event import WorkflowEvent, iso_now

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\btvly-[A-Za-z0-9\-]{16,}\b"),
)


def _redact_text(text: str) -> str:
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    final_answer TEXT,
                    error TEXT,
                    approval_state TEXT NOT NULL DEFAULT 'none',
                    tool_count INTEGER NOT NULL DEFAULT 0,
                    event_count INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(run_id, seq)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    user_goal TEXT NOT NULL,
                    successful_plan TEXT NOT NULL,
                    failed_attempts TEXT NOT NULL,
                    reusable_knowledge TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_thread_id ON runs(thread_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);")
            self.conn.commit()

    def create_run(self, run_id: str, thread_id: str, mode: str, user_input: str) -> None:
        now = iso_now()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO runs (run_id, thread_id, mode, status, user_input, created_at, updated_at)
                VALUES (?, ?, ?, 'running', ?, ?, ?)
                """,
                (run_id, thread_id, mode, user_input, now, now),
            )
            self.conn.commit()

    def update_run(
        self,
        run_id: str,
        *,
        status: str | None = None,
        final_answer: str | None = None,
        error: str | None = None,
        approval_state: str | None = None,
        tool_count: int | None = None,
        event_count: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        assignments: list[str] = ["updated_at = ?"]
        values: list[Any] = [iso_now()]
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if final_answer is not None:
            assignments.append("final_answer = ?")
            values.append(final_answer)
        if error is not None:
            assignments.append("error = ?")
            values.append(error)
        if approval_state is not None:
            assignments.append("approval_state = ?")
            values.append(approval_state)
        if tool_count is not None:
            assignments.append("tool_count = ?")
            values.append(tool_count)
        if event_count is not None:
            assignments.append("event_count = ?")
            values.append(event_count)
        if duration_ms is not None:
            assignments.append("duration_ms = ?")
            values.append(duration_ms)
        values.append(run_id)
        with self._lock:
            self.conn.execute(f"UPDATE runs SET {', '.join(assignments)} WHERE run_id = ?", values)
            self.conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_runs(self, limit: int = 50, thread_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if thread_id is not None:
                rows = self.conn.execute(
                    """
                    SELECT run_id, thread_id, mode, status, user_input, tool_count,
                           event_count, duration_ms, created_at, updated_at
                    FROM runs WHERE thread_id = ? ORDER BY created_at DESC LIMIT ?
                    """,
                    (thread_id, limit),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """
                    SELECT run_id, thread_id, mode, status, user_input, tool_count,
                           event_count, duration_ms, created_at, updated_at
                    FROM runs ORDER BY created_at DESC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                """
                SELECT
                    COUNT(*) AS total_runs,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed,
                    COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) AS failed,
                    COALESCE(SUM(tool_count), 0) AS total_tools,
                    COALESCE(SUM(event_count), 0) AS total_events,
                    COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
                FROM runs
                """
            ).fetchone()
            mem = self.conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
            art = self.conn.execute("SELECT COUNT(*) AS c FROM artifacts").fetchone()
        result = dict(row)
        result["total_memories"] = int(mem["c"])
        result["total_artifacts"] = int(art["c"])
        result["avg_duration_ms"] = int(result["avg_duration_ms"])
        return result

    def count_events(self, run_id: str) -> int:
        with self._lock:
            row = self.conn.execute(
                "SELECT COUNT(*) AS c FROM events WHERE run_id = ?", (run_id,)
            ).fetchone()
        return int(row["c"])

    def count_tool_events(self, run_id: str) -> int:
        with self._lock:
            row = self.conn.execute(
                "SELECT COUNT(*) AS c FROM events WHERE run_id = ? AND event_json LIKE '%\"tool.completed\"%'",
                (run_id,),
            ).fetchone()
        return int(row["c"])

    def next_seq(self, run_id: str) -> int:
        with self._lock:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return int(row["max_seq"]) + 1

    def append_event(self, event: WorkflowEvent) -> None:
        payload = _redact_text(event.model_dump_json())
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO events (run_id, seq, event_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event.run_id, event.seq, payload, iso_now()),
            )
            self.conn.commit()

    def list_events_after(self, run_id: str, after_seq: int) -> list[WorkflowEvent]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT event_json FROM events
                WHERE run_id = ? AND seq > ?
                ORDER BY seq ASC
                """,
                (run_id, after_seq),
            ).fetchall()
        return [WorkflowEvent.model_validate(json.loads(r["event_json"])) for r in rows]

    def create_artifact(self, run_id: str, kind: str, title: str, content: str) -> None:
        safe_title = _redact_text(title)
        safe_content = _redact_text(content)
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO artifacts (run_id, kind, title, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, kind, safe_title, safe_content, iso_now()),
            )
            self.conn.commit()

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, kind, title, content, created_at FROM artifacts WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_artifact(self, artifact_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT id, run_id, kind, title, content, created_at FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_memory(
        self,
        memory_id: str,
        run_id: str,
        task_type: str,
        user_goal: str,
        successful_plan: list[str],
        failed_attempts: list[str],
        reusable_knowledge: list[str],
    ) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO memories
                (memory_id, run_id, task_type, user_goal, successful_plan, failed_attempts, reusable_knowledge, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    run_id,
                    task_type,
                    user_goal,
                    json.dumps(successful_plan, ensure_ascii=False),
                    json.dumps(failed_attempts, ensure_ascii=False),
                    json.dumps(reusable_knowledge, ensure_ascii=False),
                    iso_now(),
                ),
            )
            self.conn.commit()

    def list_memories(self, run_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            if run_id is not None:
                rows = self.conn.execute(
                    "SELECT * FROM memories WHERE run_id = ? ORDER BY created_at DESC LIMIT ?",
                    (run_id, limit),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        result: list[dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            for key in ("successful_plan", "failed_attempts", "reusable_knowledge"):
                try:
                    item[key] = json.loads(item[key])
                except (json.JSONDecodeError, TypeError):
                    item[key] = []
            result.append(item)
        return result

    def close(self) -> None:
        with self._lock:
            self.conn.close()
