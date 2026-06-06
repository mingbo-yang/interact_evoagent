"""Tests for the model-facing todo tools (P0.4)."""

import json

import pytest

from evoagent.tools.builtin import create_builtin_registry
from evoagent.tools.todo_tools import TodoStore


def test_store_set_and_format(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    warnings = store.set([
        {"content": "Read code", "status": "done"},
        {"content": "Write fix", "status": "in_progress"},
        {"content": "Run tests", "status": "pending"},
    ])
    assert warnings == []
    assert store.progress() == "1/3 done"
    fmt = store.format()
    assert "[x] Read code" in fmt
    assert "[~] Write fix" in fmt
    assert "[ ] Run tests" in fmt


def test_store_persists_and_reloads(tmp_path):
    path = tmp_path / "todos.json"
    store = TodoStore(path)
    store.set([{"content": "task A", "status": "pending"}])
    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw[0]["content"] == "task A"
    # New store over same path resumes the list.
    store2 = TodoStore(path)
    assert len(store2.items) == 1
    assert store2.items[0].content == "task A"


def test_store_rejects_bad_status_and_warns(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    warnings = store.set([{"content": "x", "status": "frozen"}])
    assert store.items[0].status == "pending"
    assert any("unknown status" in w for w in warnings)


def test_store_warns_multiple_in_progress(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    warnings = store.set([
        {"content": "a", "status": "in_progress"},
        {"content": "b", "status": "in_progress"},
    ])
    assert any("in_progress" in w for w in warnings)


def test_store_skips_empty_content(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    store.set([{"content": "  ", "status": "pending"}, {"content": "real"}])
    assert len(store.items) == 1
    assert store.items[0].content == "real"


@pytest.mark.asyncio
async def test_write_and_list_todos_via_registry(tmp_path):
    reg = create_builtin_registry(tmp_path)
    assert "write_todos" in reg.list_tools()
    assert "list_todos" in reg.list_tools()
    res = await reg.run_tool("write_todos", {"todos": [
        {"content": "step 1", "status": "in_progress"},
        {"content": "step 2", "status": "pending"},
    ]})
    assert res.success
    assert "step 1" in res.output
    listed = await reg.run_tool("list_todos", {})
    assert listed.success
    assert "step 2" in listed.output
    # Store is exposed on the registry and persisted.
    assert reg.todo_store is not None
    assert len(reg.todo_store.items) == 2
    assert (tmp_path / ".evoagent" / "todos.json").exists()


@pytest.mark.asyncio
async def test_write_todos_replaces_list(tmp_path):
    reg = create_builtin_registry(tmp_path)
    await reg.run_tool("write_todos", {"todos": [{"content": "old"}]})
    await reg.run_tool("write_todos", {"todos": [
        {"content": "new1"}, {"content": "new2"}]})
    contents = [i.content for i in reg.todo_store.items]
    assert contents == ["new1", "new2"]


@pytest.mark.asyncio
async def test_todos_disabled(tmp_path):
    reg = create_builtin_registry(tmp_path, enable_todos=False)
    assert "write_todos" not in reg.list_tools()
    assert reg.todo_store is None
