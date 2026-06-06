"""Crash-recovery checkpoints for agent runs.

A :class:`RunCheckpointer` persists the evolving message history of a run to a
single JSON file using an atomic write (write-temp + ``os.replace``), so a
process crash mid-run leaves a consistent file that can be resumed. The engine
checkpoints after every assistant turn and tool round; a resume reloads the
messages and continues the ReAct loop from where it stopped.

Secrets are redacted before persistence (consistent with the rest of the
session/trace persistence layer).
"""

import json
import os
from pathlib import Path
from typing import Any

from evoagent.core.redaction import redact_obj
from evoagent.core.time import utc_now_iso

_CHECKPOINT_FILE = "checkpoint.json"


class RunCheckpointer:
    """Atomically persists a single run's resumable state."""

    def __init__(self, run_dir: str | Path, run_id: str, task: str = ""):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.task = task
        self.path = self.run_dir / _CHECKPOINT_FILE

    def save(
        self,
        messages: list,
        *,
        status: str = "running",
        stop_reason: str = "",
        system_prompt: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Atomically write the current run state."""
        data: dict[str, Any] = {
            "run_id": self.run_id,
            "task": self.task,
            "status": status,
            "stop_reason": stop_reason,
            "system_prompt": system_prompt,
            "updated_at": utc_now_iso(),
            "messages": [m.model_dump(mode="json") for m in messages],
        }
        if extra:
            data.update(extra)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(redact_obj(data), ensure_ascii=False))
        os.replace(tmp, self.path)

    @classmethod
    def load(cls, run_dir: str | Path) -> dict[str, Any] | None:
        """Load a checkpoint dict from a run directory, or None if absent."""
        p = Path(run_dir) / _CHECKPOINT_FILE
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


class CheckpointStore:
    """Directory of run checkpoints, one subdirectory per run_id."""

    def __init__(self, base_dir: str | Path = ".runs"):
        self.base = Path(base_dir)

    def checkpointer(self, run_id: str, task: str = "") -> RunCheckpointer:
        return RunCheckpointer(self.base / run_id, run_id, task)

    def load(self, run_id: str) -> dict[str, Any] | None:
        return RunCheckpointer.load(self.base / run_id)

    def list_runs(self) -> list[str]:
        if not self.base.exists():
            return []
        return sorted(
            d.name for d in self.base.iterdir()
            if d.is_dir() and (d / _CHECKPOINT_FILE).exists()
        )

    def latest(self) -> dict[str, Any] | None:
        runs = [
            d for d in self.base.glob("*")
            if d.is_dir() and (d / _CHECKPOINT_FILE).exists()
        ] if self.base.exists() else []
        if not runs:
            return None
        runs.sort(key=lambda p: (p / _CHECKPOINT_FILE).stat().st_mtime, reverse=True)
        return RunCheckpointer.load(runs[0])
