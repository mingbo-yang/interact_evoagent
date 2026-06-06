"""Tests for workspace snapshots and the undo_last tool (P0.3)."""

import pytest

from evoagent.tools.builtin import create_builtin_registry
from evoagent.tools.snapshots import WorkspaceSnapshotManager, apply_writes

# ── Manager unit tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_and_undo_restores_modified_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("original\n")
    mgr = WorkspaceSnapshotManager(tmp_path)
    await apply_writes(mgr, {f: "modified\n"}, "edit_file")
    assert f.read_text() == "modified\n"
    summary = mgr.undo_last()
    assert summary["ok"]
    assert f.read_text() == "original\n"
    assert "a.txt" in summary["restored"]


@pytest.mark.asyncio
async def test_undo_removes_newly_created_file(tmp_path):
    f = tmp_path / "new.txt"
    mgr = WorkspaceSnapshotManager(tmp_path)
    await apply_writes(mgr, {f: "hello\n"}, "write_file")
    assert f.exists()
    summary = mgr.undo_last()
    assert summary["ok"]
    assert not f.exists()
    assert "new.txt" in summary["deleted"]


@pytest.mark.asyncio
async def test_stacked_undo_steps_back(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("v0\n")
    mgr = WorkspaceSnapshotManager(tmp_path)
    await apply_writes(mgr, {f: "v1\n"}, "edit_file")
    await apply_writes(mgr, {f: "v2\n"}, "edit_file")
    assert f.read_text() == "v2\n"
    mgr.undo_last()
    assert f.read_text() == "v1\n"
    mgr.undo_last()
    assert f.read_text() == "v0\n"
    assert not mgr.has_undo()


def test_undo_nothing(tmp_path):
    mgr = WorkspaceSnapshotManager(tmp_path)
    summary = mgr.undo_last()
    assert not summary["ok"]
    assert "Nothing" in summary["error"]


@pytest.mark.asyncio
async def test_crash_recovery_rebuilds_journal(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("orig\n")
    mgr = WorkspaceSnapshotManager(tmp_path)
    await apply_writes(mgr, {f: "changed\n"}, "edit_file")
    # Simulate a fresh process: new manager over the same workspace.
    mgr2 = WorkspaceSnapshotManager(tmp_path)
    assert mgr2.has_undo()
    summary = mgr2.undo_last()
    assert summary["ok"]
    assert f.read_text() == "orig\n"


def test_rebuild_ignores_partial_group(tmp_path):
    mgr = WorkspaceSnapshotManager(tmp_path)
    # A leftover temp dir (crash before atomic rename) and a numbered dir with
    # no manifest must both be ignored / cleaned up.
    (mgr.dir / ".tmp-7").mkdir(parents=True)
    (mgr.dir / "3").mkdir(parents=True)
    mgr2 = WorkspaceSnapshotManager(tmp_path)
    assert not mgr2.has_undo()


@pytest.mark.asyncio
async def test_multifile_group_undo_restores_all(tmp_path):
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"
    f1.write_text("a\n")
    f2.write_text("b\n")
    mgr = WorkspaceSnapshotManager(tmp_path)
    await apply_writes(mgr, {f1: "A\n", f2: "B\n"}, "apply_patch")
    mgr.undo_last()
    assert f1.read_text() == "a\n"
    assert f2.read_text() == "b\n"


@pytest.mark.asyncio
async def test_internal_paths_not_snapshotted(tmp_path):
    mgr = WorkspaceSnapshotManager(tmp_path)
    internal = mgr.dir / "x.bak"
    seq = mgr.record([internal], "edit_file")
    assert seq is None  # nothing recorded for internal paths


# ── Tool/registry integration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_edit_then_undo_via_registry(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x = 1\n")
    reg = create_builtin_registry(tmp_path)
    assert "undo_last" in reg.list_tools()
    await reg.run_tool("edit_file", {"path": "code.py",
                                     "old_text": "x = 1", "new_text": "x = 2"})
    assert "x = 2" in f.read_text()
    res = await reg.run_tool("undo_last", {})
    assert res.success
    assert f.read_text() == "x = 1\n"


@pytest.mark.asyncio
async def test_write_then_undo_via_registry(tmp_path):
    reg = create_builtin_registry(tmp_path)
    await reg.run_tool("write_file", {"path": "fresh.txt", "content": "hi"})
    assert (tmp_path / "fresh.txt").exists()
    res = await reg.run_tool("undo_last", {})
    assert res.success
    assert not (tmp_path / "fresh.txt").exists()


@pytest.mark.asyncio
async def test_undo_nothing_via_registry(tmp_path):
    reg = create_builtin_registry(tmp_path)
    res = await reg.run_tool("undo_last", {})
    assert not res.success


@pytest.mark.asyncio
async def test_undo_disabled(tmp_path):
    reg = create_builtin_registry(tmp_path, enable_undo=False)
    assert "undo_last" not in reg.list_tools()
    # Writes still work without snapshots.
    await reg.run_tool("write_file", {"path": "z.txt", "content": "ok"})
    assert (tmp_path / "z.txt").read_text() == "ok"
