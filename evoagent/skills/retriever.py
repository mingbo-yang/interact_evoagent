"""SkillRetriever — find relevant skills for a task."""

from __future__ import annotations

from evoagent.skills.registry import SkillRegistry
from evoagent.skills.schema import Skill


class SkillRetriever:
    """Retrieve skills matching a task, error, or context.

    Scoring:
    - trigger match: +10 per matching trigger word
    - name/description match: +2 per word
    - Boost for high success_count, penalty for high failure_count
    """

    def __init__(self, registry: SkillRegistry, top_k: int = 3):
        self.registry = registry
        self.top_k = top_k

    def retrieve(
        self, task: str, context: str | None = None, error: str | None = None, top_k: int | None = None
    ) -> list[Skill]:
        """Retrieve top-k skills matching the task/context/error.

        Args:
            task: The current task description.
            context: Additional context.
            error: Error message if task failed.
            top_k: Override default top_k.

        Returns:
            Ranked list of Skill objects.
        """
        query = f"{task} {context or ''} {error or ''}".lower()
        matches = self.registry.search_by_trigger(query)

        # Adjust ranking by usage stats
        for skill in matches:
            skill.metadata["_score"] = skill.metadata.get("_score", 1)
            if skill.success_count > 0:
                skill.metadata["_score"] = skill.metadata.get("_score", 1) + min(skill.success_count, 10)
            if skill.failure_count > 0:
                skill.metadata["_score"] = skill.metadata.get("_score", 1) - min(skill.failure_count, 10)

        k = top_k or self.top_k
        return matches[:k]

    def format_for_prompt(self, skills: list[Skill]) -> str:
        """Format skills into a prompt-injectable block."""
        if not skills:
            return ""
        lines = ["## Relevant Skills"]
        for i, s in enumerate(skills, 1):
            lines.append(f"### {i}. {s.name}")
            lines.append(f"{s.description}")
            lines.append(f"{s.content[:500]}")
            lines.append("")
        return "\n".join(lines)
