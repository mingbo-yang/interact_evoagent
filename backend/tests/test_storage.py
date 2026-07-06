"""Unit tests for the SQLite storage layer (no network / no LLM)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.schemas.workflow_event import WorkflowEvent
from app.storage.db import Database, _redact_text


def _make_db() -> tuple[Database, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    db = Database(Path(tmp.name) / "test.db")
    return db, tmp


def _teardown(db: Database, tmp: tempfile.TemporaryDirectory) -> None:
    db.close()
    tmp.cleanup()


def test_run_lifecycle_and_seq():
    db, tmp = _make_db()
    try:
        db.create_run("run_a", "thread_a", "mock", "hello")
        assert db.next_seq("run_a") == 1
        evt = WorkflowEvent(
            event_id="evt_1", event_type="run.started", run_id="run_a",
            thread_id="thread_a", seq=db.next_seq("run_a"), status="running",
        )
        db.append_event(evt)
        assert db.next_seq("run_a") == 2
        db.update_run("run_a", status="completed", final_answer="done")
        row = db.get_run("run_a")
        assert row is not None
        assert row["status"] == "completed"
        assert row["final_answer"] == "done"
    finally:
        _teardown(db, tmp)


def test_events_ordered_by_seq():
    db, tmp = _make_db()
    try:
        db.create_run("run_b", "thread_b", "mock", "hi")
        for i in range(1, 6):
            db.append_event(WorkflowEvent(
                event_id=f"evt_{i}", event_type="node.completed", run_id="run_b",
                thread_id="thread_b", seq=i, status="success",
            ))
        events = db.list_events_after("run_b", 0)
        assert [e.seq for e in events] == [1, 2, 3, 4, 5]
        partial = db.list_events_after("run_b", 3)
        assert [e.seq for e in partial] == [4, 5]
    finally:
        _teardown(db, tmp)


def test_secret_redaction_in_events_and_artifacts():
    db, tmp = _make_db()
    try:
        db.create_run("run_c", "thread_c", "mock", "x")
        leaky = "key sk-abcdefghijklmnopqrstuvwx and tvly-abcdefghijklmnopqrst"
        db.append_event(WorkflowEvent(
            event_id="evt_1", event_type="node.completed", run_id="run_c",
            thread_id="thread_c", seq=1, visible_output=leaky,
        ))
        events = db.list_events_after("run_c", 0)
        assert "sk-abcdefghijklmnopqrstuvwx" not in events[0].visible_output
        assert "[REDACTED]" in events[0].visible_output

        db.create_artifact("run_c", "tool_output", "t", leaky)
        arts = db.list_artifacts("run_c")
        assert "sk-abcdefghijklmnopqrstuvwx" not in arts[0]["content"]
    finally:
        _teardown(db, tmp)


def test_memory_roundtrip():
    db, tmp = _make_db()
    try:
        db.create_run("run_d", "thread_d", "mock", "goal")
        db.create_memory(
            "mem_1", "run_d", "interactive_workflow", "goal",
            ["step1", "step2"], [], ["knowledge"],
        )
        mems = db.list_memories("run_d")
        assert len(mems) == 1
        assert mems[0]["successful_plan"] == ["step1", "step2"]
        assert mems[0]["reusable_knowledge"] == ["knowledge"]
    finally:
        _teardown(db, tmp)


def test_redact_helper():
    assert _redact_text("sk-1234567890abcdef1234") == "[REDACTED]"
    assert _redact_text("safe text") == "safe text"
