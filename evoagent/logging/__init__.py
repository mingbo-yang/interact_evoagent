"""Event logging and trace recording.

Provides:
- JSONLEventLogger: append events to JSONL files
- TraceRecorder: manage run directories with full trace
- CheckpointManager: save/load RuntimeState checkpoints
- DiffRecorder: generate and save unified diffs
- Event, EventType: core event schema (from event.py)
"""

from evoagent.logging.checkpoint import CheckpointManager  # noqa: F401
from evoagent.logging.diff import DiffRecorder  # noqa: F401
from evoagent.logging.event import Event, EventType  # noqa: F401
from evoagent.logging.jsonl_logger import JSONLEventLogger  # noqa: F401
from evoagent.logging.trace import TraceRecorder  # noqa: F401
