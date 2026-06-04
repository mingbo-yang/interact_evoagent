"""JSONLEventLogger — append events to a JSONL file with filtering support."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from evoagent.logging.event import Event, EventType


class JSONLEventLogger:
    """Append-only JSONL event logger.

    Each event is written as a single JSON line to a .jsonl file.
    Supports filtering, pagination, and streaming reads.

    Usage:
        logger = JSONLEventLogger("events.jsonl")
        logger.log_event(event)
        events = logger.get_events(run_id="run_abc", limit=100)
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(str(self.path), "a", encoding="utf-8")

    def log_event(self, event: Event) -> None:
        line = event.model_dump_json(ensure_ascii=False)
        self._file.write(line + "\n")
        self._file.flush()

    def log(
        self,
        event_type: EventType | str,
        payload: dict[str, Any] | None = None,
        run_id: str = "",
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            event_type=EventType(event_type) if isinstance(event_type, str) else event_type,
            payload=payload or {}, run_id=run_id, step_id=step_id, metadata=metadata or {},
        )
        self.log_event(event)
        return event

    def get_events(
        self,
        run_id: str | None = None,
        event_type: EventType | str | None = None,
        limit: int = 1000,
        offset: int = 0,
        reverse: bool = False,
        since_timestamp: str | None = None,
    ) -> list[Event]:
        """Read events with filtering and pagination.

        Args:
            run_id: Filter by run_id.
            event_type: Filter by event type.
            limit: Max events to return (default 1000, 0 = unlimited).
            offset: Skip this many matching events.
            reverse: If True, read newest first.
            since_timestamp: Only return events after this ISO-8601 timestamp.

        Returns:
            Filtered list of Event objects.
        """
        if not self.path.exists():
            return []
        events = list(self.iter_events(run_id=run_id, event_type=event_type,
                                        since_timestamp=since_timestamp))
        if reverse:
            events.reverse()
        if offset > 0:
            events = events[offset:]
        if limit > 0:
            events = events[:limit]
        return events

    def iter_events(
        self,
        run_id: str | None = None,
        event_type: EventType | str | None = None,
        since_timestamp: str | None = None,
    ) -> Iterator[Event]:
        """Stream events one at a time (generator, not full list).

        Args:
            run_id: Filter by run_id.
            event_type: Filter by event type.
            since_timestamp: Only yield events after this timestamp.

        Yields:
            Event objects matching filters.
        """
        if not self.path.exists():
            return
        et = EventType(event_type) if isinstance(event_type, str) and event_type else event_type
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = Event.model_validate_json(line)
                except Exception:
                    continue
                if run_id and evt.run_id != run_id:
                    continue
                if et and evt.event_type != et:
                    continue
                if since_timestamp and evt.timestamp <= since_timestamp:
                    continue
                yield evt

    def tail_events(self, n: int = 100) -> list[Event]:
        """Return the last N events (newest first)."""
        return self.get_events(limit=n, reverse=True)

    def get_run_ids(self) -> set[str]:
        ids: set[str] = set()
        if not self.path.exists():
            return ids
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "run_id" in data:
                        ids.add(data["run_id"])
                except json.JSONDecodeError:
                    continue
        return ids

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "JSONLEventLogger":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
