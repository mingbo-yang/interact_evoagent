"""Steering / interrupt control for the ReAct loop.

A :class:`SteeringController` lets an out-of-band caller (an interactive UI or a
supervising coroutine) steer or interrupt a running agent at *safe* checkpoints
without breaking the assistant/tool message invariant.

Controls:
- ``inject(text)`` — queue a user message inserted before the next model call
  (e.g. "change the plan", "run the tests now").
- ``request_stop()`` — finish the current tool round, then halt gracefully
  ("stop after current tool").
- ``cancel()`` — hard stop; additionally cancels an in-flight tool execution
  (e.g. a long-running shell command).
- ``forbid_file(path)`` — make the engine deny writes to a path
  ("don't touch file X").

Producer methods are safe to call from another task; the engine consumes the
state at checkpoints.
"""

import asyncio
import threading
from pathlib import Path


class SteeringController:
    """Thread/task-safe steering state shared between a UI and the engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._injections: list[str] = []
        self._stop = False
        self._cancel_event = asyncio.Event()
        self._forbidden: set[str] = set()

    # ── producer side (UI / supervisor) ──────────────────────────────
    def inject(self, text: str) -> None:
        """Queue a user message to insert before the next model call."""
        if text and text.strip():
            with self._lock:
                self._injections.append(text.strip())

    def request_stop(self) -> None:
        """Halt gracefully after the current tool round completes."""
        self._stop = True

    def cancel(self) -> None:
        """Hard stop and cancel any in-flight tool execution."""
        self._stop = True
        self._cancel_event.set()

    def forbid_file(self, path: str) -> None:
        """Deny subsequent writes to ``path`` (matched by exact path or name)."""
        with self._lock:
            self._forbidden.add(self._norm(path))

    # ── consumer side (engine) ───────────────────────────────────────
    def drain_injections(self) -> list[str]:
        """Return and clear any queued injection messages."""
        with self._lock:
            items = self._injections
            self._injections = []
            return items

    @property
    def stop_requested(self) -> bool:
        return self._stop

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def cancel_event(self) -> asyncio.Event:
        return self._cancel_event

    def is_forbidden(self, target: str) -> bool:
        """True if ``target`` matches a forbidden path (exact, suffix, or name)."""
        if not target:
            return False
        t = self._norm(target)
        tname = Path(t).name
        with self._lock:
            for f in self._forbidden:
                if t == f or t.endswith("/" + f) or tname == Path(f).name:
                    return True
        return False

    @staticmethod
    def _norm(path: str) -> str:
        return str(path).replace("\\", "/").strip()
