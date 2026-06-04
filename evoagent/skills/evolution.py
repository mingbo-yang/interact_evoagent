"""SkillEvolution — rule-based skill priority adjustment."""

from __future__ import annotations

from evoagent.skills.registry import SkillRegistry


class SkillEvolution:
    """Adjust skill priorities based on usage history.

    Rule-based (no LLM):
    - High success rate → increase priority
    - High failure rate → lower priority
    - Stale skills (not used recently) → slight decay

    Future: LLM-based skill refinement.
    """

    def __init__(self, registry: SkillRegistry,
                 success_threshold: float = 0.8,
                 failure_threshold: float = 0.3,
                 min_samples: int = 5):
        self.registry = registry
        self.success_threshold = success_threshold
        self.failure_threshold = failure_threshold
        self.min_samples = min_samples

    def evolve(self) -> list[str]:
        """Evolve all skills. Returns names of modified skills."""
        modified: list[str] = []
        for skill in self.registry.list():
            changed = False
            total = skill.success_count + skill.failure_count
            if total >= self.min_samples:
                ratio = skill.success_count / total
                if ratio >= self.success_threshold:
                    skill.metadata["priority"] = "high"
                    changed = True
                elif ratio <= self.failure_threshold:
                    skill.metadata["priority"] = "low"
                    changed = True
            if changed:
                modified.append(skill.name)
        return modified
