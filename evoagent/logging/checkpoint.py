"""CheckpointManager — save and load RuntimeState checkpoints."""

import json
from pathlib import Path
from typing import Any

from evoagent.core.ids import generate_id
from evoagent.core.state import Checkpoint, RuntimeState
from evoagent.core.time import utc_now_iso


class CheckpointManager:
    """Manages checkpoint save/load for a run.

    Checkpoints are saved as JSON files with the RuntimeState
    and optional metadata.

    Usage:
        mgr = CheckpointManager("/path/to/.evoagent/checkpoints")
        chk = mgr.save_checkpoint(state, name="before_edit")
        state = mgr.load_checkpoint("run_abc", chk.id)
    """

    def __init__(self, base_dir: str | Path = ".evoagent/checkpoints"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        d = self.base_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_checkpoint(
        self,
        state: RuntimeState,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Save a RuntimeState as a checkpoint file.

        Args:
            state: The runtime state to save.
            name: Optional human-readable name.
            metadata: Extra metadata.

        Returns:
            The created Checkpoint object.
        """
        run_id = state.run_id
        chk_id = generate_id("chk")
        timestamp = utc_now_iso()

        checkpoint = Checkpoint(
            id=chk_id,
            state=state,
            timestamp=timestamp,
            can_resume=True,
            metadata=metadata or {},
        )

        # Save to file
        run_dir = self._run_dir(run_id)
        filename = f"{chk_id}.json"
        if name:
            filename = f"{chk_id}_{name}.json"
        filepath = run_dir / filename
        filepath.write_text(
            json.dumps(checkpoint.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Also write latest pointer
        latest_meta = {"checkpoint_id": chk_id, "name": name, "timestamp": timestamp}
        (run_dir / "latest.json").write_text(
            json.dumps(latest_meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return checkpoint

    def load_checkpoint(
        self,
        run_id: str,
        checkpoint_id: str | None = None,
    ) -> Checkpoint | None:
        """Load a checkpoint.

        Args:
            run_id: The run ID.
            checkpoint_id: Specific checkpoint ID. If None, loads the latest.

        Returns:
            The Checkpoint, or None if not found.
        """
        run_dir = self._run_dir(run_id)

        if checkpoint_id:
            # Find the file matching this checkpoint_id
            for f in sorted(run_dir.glob("chk_*.json")):
                if f.stem.startswith(checkpoint_id):
                    return Checkpoint.model_validate_json(f.read_text(encoding="utf-8"))
            return None

        # Load latest
        latest_path = run_dir / "latest.json"
        if not latest_path.exists():
            # Fall back to most recent checkpoint file
            files = sorted(run_dir.glob("chk_*.json"), reverse=True)
            if not files:
                return None
            return Checkpoint.model_validate_json(files[0].read_text(encoding="utf-8"))

        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        chk_id = latest["checkpoint_id"]

        for f in sorted(run_dir.glob("chk_*.json")):
            if f.stem.startswith(chk_id):
                return Checkpoint.model_validate_json(f.read_text(encoding="utf-8"))

        return None

    def list_checkpoints(self, run_id: str) -> list[dict[str, Any]]:
        """List all checkpoints for a run.

        Args:
            run_id: The run ID.

        Returns:
            List of {checkpoint_id, name, timestamp} dicts.
        """
        run_dir = self._run_dir(run_id)
        result: list[dict[str, Any]] = []
        for f in sorted(run_dir.glob("chk_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                result.append({
                    "checkpoint_id": data.get("id", f.stem),
                    "timestamp": data.get("timestamp", ""),
                    "can_resume": data.get("can_resume", True),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return result
