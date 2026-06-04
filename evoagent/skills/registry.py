"""SkillRegistry — register, look up, and track skill usage."""

from __future__ import annotations

from evoagent.core.time import utc_now_iso
from evoagent.skills.schema import Skill


class SkillRegistry:
    """Central registry for skills.

    Supports register, get, list, search_by_trigger, and usage tracking.
    Duplicate names are overwritten by default (latest wins).
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill. Overwrites if name already exists."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list(self) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.name)

    def search_by_trigger(self, query: str) -> list[Skill]:
        """Find skills whose triggers match the query."""
        q = query.lower()
        matches: list[tuple[int, Skill]] = []
        for skill in self._skills.values():
            score = 0
            for t in skill.triggers:
                if t in q:
                    score += 10
            for word in q.split():
                if word in skill.name.lower() or word in skill.description.lower():
                    score += 2
            if score > 0:
                matches.append((score, skill))
        matches.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in matches]

    def update_usage(self, name: str, success: bool) -> None:
        """Update success/failure counts and last_used_at."""
        skill = self._skills.get(name)
        if not skill:
            return
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1
        skill.last_used_at = utc_now_iso()

    def __len__(self) -> int:
        return len(self._skills)
