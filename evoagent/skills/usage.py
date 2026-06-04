"""SkillUsageTracker — persist usage statistics."""

import json
from pathlib import Path

from evoagent.core.time import utc_now_iso
from evoagent.skills.registry import SkillRegistry


class SkillUsageTracker:
    """Track skill usage events and persist stats to JSON.

    Usage:
        tracker = SkillUsageTracker(registry, ".evoagent/skills_usage.json")
        tracker.record_usage("debugging_python", success=True)
        tracker.save()
    """

    def __init__(self, registry: SkillRegistry, stats_path: str | Path = ".evoagent/skills_usage.json"):
        self.registry = registry
        self.stats_path = Path(stats_path)
        self._events: list[dict] = []

    def record_usage(self, skill_name: str, success: bool, task: str = "") -> None:
        """Record a skill usage event."""
        self._events.append({
            "skill": skill_name,
            "success": success,
            "task": task,
            "timestamp": utc_now_iso(),
        })
        self.registry.update_usage(skill_name, success)

    def save(self) -> None:
        """Persist usage events to JSON file."""
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if self.stats_path.exists():
            try:
                existing = json.loads(self.stats_path.read_text())
            except json.JSONDecodeError:
                pass
        existing.extend(self._events)
        self.stats_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        self._events.clear()

    def load_stats(self) -> list[dict]:
        """Load saved usage statistics."""
        if not self.stats_path.exists():
            return []
        try:
            return json.loads(self.stats_path.read_text())
        except json.JSONDecodeError:
            return []
