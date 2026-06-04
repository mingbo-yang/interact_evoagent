"""Skill agent example — load builtin skills and retrieve for a debugging task."""

import asyncio
from pathlib import Path

from evoagent.skills.loader import SkillLoader
from evoagent.skills.registry import SkillRegistry
from evoagent.skills.retriever import SkillRetriever

BUILTIN_DIR = Path(__file__).parent.parent / "evoagent" / "skills" / "builtin"


async def main():
    # Load builtin skills
    registry = SkillRegistry()
    skills = SkillLoader.load_dir(BUILTIN_DIR)
    for s in skills:
        registry.register(s)
    print(f"Loaded {len(registry)} skills: {[s.name for s in registry.list()]}")

    # Simulate a debugging task
    retriever = SkillRetriever(registry)
    matched = retriever.retrieve(
        task="Fix a failing pytest",
        error="AssertionError: assert 5 == 6 in test_calculator.py::test_add",
    )
    print(f"\nMatched {len(matched)} skills:")
    for s in matched:
        print(f"  - {s.name}: {s.description}")

    # Format for prompt
    formatted = retriever.format_for_prompt(matched)
    print(f"\nPrompt injection:\n{formatted[:500]}...")


if __name__ == "__main__":
    asyncio.run(main())
