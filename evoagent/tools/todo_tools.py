"""Model-facing todo / task-list tools (P0.4).

A lightweight, in-context task list the model maintains while working a
multi-step task. The model calls ``write_todos`` to set the whole list (with
per-item status) and ``list_todos`` to read it back. The full-replace design
(rather than per-id create/update) keeps the model's view and the stored list
in sync and avoids dangling ids.

The list is persisted to ``<workspace>/.evoagent/todos.json`` so it survives a
crash/resume and can be re-injected into context after compaction (P0.6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.schema import ToolResult

VALID_STATUSES = ("pending", "in_progress", "done", "blocked")
_STATUS_MARK = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]", "blocked": "[!]"}


@dataclass
class TodoItem:
    content: str
    status: str = "pending"
    note: str = ""


class TodoStore:
    """Holds the current todo list and persists it to disk."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.items: list[TodoItem] = []
        self._load()

    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [
                TodoItem(content=str(d.get("content", "")),
                         status=d.get("status", "pending") if d.get("status") in VALID_STATUSES
                         else "pending",
                         note=str(d.get("note", "")))
                for d in data if str(d.get("content", "")).strip()
            ]
        except Exception:
            self.items = []

    def _save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps([vars(i) for i in self.items], ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass

    def set(self, raw_items: list) -> list[str]:
        """Replace the whole list. Returns a list of validation warnings."""
        warnings: list[str] = []
        items: list[TodoItem] = []
        for d in raw_items:
            if isinstance(d, dict):
                content = str(d.get("content", "")).strip()
                status = d.get("status", "pending")
                note = str(d.get("note", ""))
            else:
                content = str(getattr(d, "content", "")).strip()
                status = getattr(d, "status", "pending")
                note = str(getattr(d, "note", ""))
            if not content:
                continue
            if status not in VALID_STATUSES:
                warnings.append(f"unknown status {status!r} for {content!r}; using 'pending'")
                status = "pending"
            items.append(TodoItem(content=content, status=status, note=note))
        active = [i for i in items if i.status == "in_progress"]
        if len(active) > 1:
            warnings.append("more than one task marked in_progress; prefer exactly one")
        self.items = items
        self._save()
        return warnings

    def format(self) -> str:
        if not self.items:
            return "(no todos)"
        lines = []
        for i in self.items:
            mark = _STATUS_MARK.get(i.status, "[ ]")
            suffix = f"  — {i.note}" if i.note else ""
            lines.append(f"{mark} {i.content}{suffix}")
        return "\n".join(lines)

    def progress(self) -> str:
        done = sum(1 for i in self.items if i.status == "done")
        return f"{done}/{len(self.items)} done" if self.items else "0/0"


# ── Tools ─────────────────────────────────────────────────────────────


class TodoItemInput(BaseModel):
    content: str = Field(..., description="The task description.")
    status: str = Field(default="pending",
                        description="One of: pending, in_progress, done, blocked.")
    note: str = Field(default="", description="Optional short note (e.g. why blocked).")


class WriteTodosInput(BaseModel):
    todos: list[TodoItemInput] = Field(
        ..., description="The COMPLETE task list, replacing any previous list. Mark exactly "
        "one task in_progress while you work it, move it to done, then start the next.")


class WriteTodosTool(BaseTool):
    name = "write_todos"
    description = ("Create or update the task list for a multi-step task. Pass the COMPLETE "
                   "list each time (it replaces the previous one). Statuses: pending, "
                   "in_progress, done, blocked. Keep exactly one task in_progress. Use this "
                   "to plan before starting and to track progress as you go.")
    input_schema = WriteTodosInput
    risk_level = RiskLevel.LOW

    def __init__(self, store: TodoStore):
        self.store = store

    async def run(self, todos: list) -> ToolResult:
        try:
            warnings = self.store.set(todos)
            out = f"Task list updated ({self.store.progress()}):\n{self.store.format()}"
            if warnings:
                out += "\n\nNote: " + "; ".join(warnings)
            return ToolResult(call_id=generate_id("call"), name=self.name, success=True,
                              output=out, metadata={"count": len(self.store.items),
                                                    "progress": self.store.progress()})
        except Exception as e:
            return ToolResult(call_id=generate_id("call"), name=self.name,
                              success=False, error=str(e))


class ListTodosInput(BaseModel):
    pass


class ListTodosTool(BaseTool):
    name = "list_todos"
    description = "Show the current task list and its progress."
    input_schema = ListTodosInput
    risk_level = RiskLevel.LOW

    def __init__(self, store: TodoStore):
        self.store = store

    async def run(self) -> ToolResult:
        return ToolResult(
            call_id=generate_id("call"), name=self.name, success=True,
            output=f"Task list ({self.store.progress()}):\n{self.store.format()}",
            metadata={"count": len(self.store.items), "progress": self.store.progress()})
