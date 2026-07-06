"""Orchestrator routing and lifecycle tests (no LLM required)."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

from app.agent.orchestrator import InteractiveOrchestrator
from app.storage.db import Database


def _make() -> tuple[InteractiveOrchestrator, Database, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    db = Database(Path(tmp.name) / "orch.db")
    orch = InteractiveOrchestrator(db=db, workspace=str(Path(tmp.name)))
    return orch, db, tmp


def test_route_shell_command_listing():
    orch, db, tmp = _make()
    try:
        cmd = orch._route_shell_command("请列出目录文件")
        assert cmd is not None
        assert cmd == orch.shell_tool.default_listing_command()
    finally:
        db.close()
        tmp.cleanup()


def test_route_shell_command_risky_triggers_approval_command():
    orch, db, tmp = _make()
    try:
        cmd = orch._route_shell_command("请执行 rm -rf 清理")
        assert cmd is not None
        assert "rm -rf" in cmd
        # And that command must be flagged as needing approval by the tool.
        assert orch.shell_tool._needs_approval(cmd) is True
    finally:
        db.close()
        tmp.cleanup()


def test_route_shell_command_none_for_plain_chat():
    orch, db, tmp = _make()
    try:
        assert orch._route_shell_command("你好，介绍一下你自己") is None
    finally:
        db.close()
        tmp.cleanup()


def test_risky_command_waits_then_rejected_records_tool_failed():
    orch, db, tmp = _make()
    try:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        db.create_run(run_id, thread_id, "evoagent", "请执行 rm -rf 清理")

        async def scenario():
            task = asyncio.create_task(
                orch._maybe_use_shell_tool(run_id, thread_id, "请执行 rm -rf 清理")
            )
            await asyncio.sleep(0.3)
            # Reject the approval.
            db.update_run(run_id, approval_state="rejected")
            return await asyncio.wait_for(task, timeout=5)

        result = asyncio.run(scenario())
        assert "not granted" in result

        events = db.list_events_after(run_id, 0)
        types = [e.event_type for e in events]
        assert "tool.started" in types
        assert "user.approval.required" in types
        assert "tool.failed" in types
    finally:
        db.close()
        tmp.cleanup()


def test_surface_agent_tool_calls_emits_events_and_artifacts():
    orch, db, tmp = _make()
    try:
        from app.agent.evoagent_wrapper import ToolCallRecord

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        db.create_run(run_id, thread_id, "evoagent", "fix a bug")
        calls = [
            ToolCallRecord(name="edit_file", success=True, output="patched foo.py"),
            ToolCallRecord(name="git_diff", success=True, output="--- a/foo.py\n+++ b/foo.py\n+fixed"),
            ToolCallRecord(name="run_tests", success=True, output="1 passed"),
            ToolCallRecord(name="bash", success=False, output="", error="boom"),
        ]
        orch._surface_agent_tool_calls(run_id, thread_id, calls)

        events = db.list_events_after(run_id, 0)
        types = [e.event_type for e in events]
        assert types.count("tool.started") == 4
        assert "tool.completed" in types
        assert "tool.failed" in types  # the failing bash call
        assert "artifact.created" in types  # git_diff / run_tests / edit_file

        arts = db.list_artifacts(run_id)
        kinds = {a["kind"] for a in arts}
        assert "git_diff" in kinds
        assert "run_tests" in kinds
        # All surfaced tool events are attributed to the evoagent source.
        tool_events = [e for e in events if e.event_type.startswith("tool.")]
        assert all(e.source == "evoagent" for e in tool_events)
    finally:
        db.close()
        tmp.cleanup()


def test_mock_run_emits_memory_updated():
    orch, db, tmp = _make()
    try:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        db.create_run(run_id, thread_id, "mock", "hello")
        asyncio.run(orch.run_mock(run_id, thread_id, "hello"))
        events = db.list_events_after(run_id, 0)
        types = [e.event_type for e in events]
        assert types[0] == "run.started"
        assert "memory.updated" in types
        assert "run.completed" in types
        seqs = [e.seq for e in events]
        assert seqs == sorted(seqs)
        assert len(seqs) == len(set(seqs))
    finally:
        db.close()
        tmp.cleanup()
