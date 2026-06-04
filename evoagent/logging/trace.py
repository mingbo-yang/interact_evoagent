"""TraceRecorder — manages run directories with events, state, and results."""

import json
from pathlib import Path
from typing import Any

from evoagent.core.ids import generate_id
from evoagent.core.result import AgentResult
from evoagent.core.state import RuntimeState
from evoagent.core.time import utc_now_iso
from evoagent.logging.event import Event, EventType
from evoagent.logging.jsonl_logger import JSONLEventLogger


class TraceRecorder:
    """Records a complete agent run trace.

    Creates a run directory with:
        .runs/<run_id>/
            events.jsonl      — all events
            state.json        — current RuntimeState
            final_result.json — AgentResult after completion
            metadata.json     — run metadata
            patches/          — file diffs (from DiffRecorder)
            artifacts/        — produced files

    Usage:
        recorder = TraceRecorder(".runs")
        recorder.start_run("Build a web app")
        recorder.record_event(...)
        recorder.save_state(state)
        recorder.save_final_result(result)
    """

    def __init__(self, base_dir: str | Path = ".runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._current_run_id: str | None = None
        self._current_dir: Path | None = None
        self._logger: JSONLEventLogger | None = None
        self._run_task: str = ""

    # ── Run lifecycle ─────────────────────────────────────────────────

    def start_run(self, task: str) -> str:
        """Start a new run and return its run_id.

        Args:
            task: The task description.

        Returns:
            The generated run_id.
        """
        run_id = generate_id("run")
        self._current_run_id = run_id
        self._current_dir = self.base_dir / run_id
        self._current_dir.mkdir(parents=True, exist_ok=True)
        (self._current_dir / "patches").mkdir(exist_ok=True)
        (self._current_dir / "artifacts").mkdir(exist_ok=True)
        self._run_task = task

        self._logger = JSONLEventLogger(self._current_dir / "events.jsonl")
        self._logger.log(
            EventType.RUN_STARTED,
            payload={"task": task},
            run_id=run_id,
        )

        # Save metadata
        meta = {
            "run_id": run_id,
            "task": task,
            "started_at": utc_now_iso(),
        }
        (self._current_dir / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False)
        )

        return run_id

    # ── Recording ─────────────────────────────────────────────────────

    def record_event(self, event: Event) -> None:
        """Record an event to the current run's event log."""
        if self._logger:
            self._logger.log_event(event)

    def log(
        self,
        event_type: EventType | str,
        payload: dict[str, Any] | None = None,
        step_id: str | None = None,
    ) -> Event | None:
        """Create and record an event for the current run."""
        if not self._current_run_id or not self._logger:
            return None
        return self._logger.log(
            event_type=event_type,
            payload=payload or {},
            run_id=self._current_run_id,
            step_id=step_id,
        )

    # ── State ─────────────────────────────────────────────────────────

    def save_state(self, state: RuntimeState) -> None:
        """Save RuntimeState to state.json in the run directory."""
        if not self._current_dir:
            return
        state.updated_at = utc_now_iso()
        state.run_id = self._current_run_id or state.run_id
        (self._current_dir / "state.json").write_text(
            state.model_dump_json(indent=2, ensure_ascii=False)
        )

    def load_state(self) -> RuntimeState | None:
        """Load RuntimeState from state.json."""
        if not self._current_dir:
            return None
        state_path = self._current_dir / "state.json"
        if not state_path.exists():
            return None
        return RuntimeState.model_validate_json(state_path.read_text(encoding="utf-8"))

    # ── Final result ──────────────────────────────────────────────────

    def save_final_result(self, result: AgentResult) -> None:
        """Save AgentResult to final_result.json."""
        if not self._current_dir:
            return
        (self._current_dir / "final_result.json").write_text(
            result.model_dump_json(indent=2, ensure_ascii=False)
        )
        if self._logger:
            self._logger.log(
                EventType.RUN_FINISHED,
                payload={"success": result.success},
                run_id=self._current_run_id,
            )

    # ── Query ─────────────────────────────────────────────────────────

    def get_events(self, event_type: EventType | str | None = None) -> list[Event]:
        """Get events from the current run."""
        if not self._logger:
            return []
        return self._logger.get_events(
            run_id=self._current_run_id,
            event_type=event_type,
        )

    def get_current_run_id(self) -> str | None:
        return self._current_run_id

    def get_current_dir(self) -> Path | None:
        return self._current_dir

    def close(self) -> None:
        if self._logger:
            self._logger.close()

    # ── Static helpers ────────────────────────────────────────────────

    def list_runs(self) -> list[str]:
        """List all run directories sorted by name."""
        if not self.base_dir.exists():
            return []
        return sorted(
            d.name for d in self.base_dir.iterdir() if d.is_dir()
        )

    def get_latest_run_dir(self) -> Path | None:
        """Return the most recently modified run directory."""
        runs = list(self.base_dir.glob("*"))
        if not runs:
            return None
        runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return runs[0]
