"""SkillLoader — load skills from markdown/YAML files."""

from pathlib import Path

import yaml

from evoagent.skills.schema import Skill


class SkillLoader:
    """Load Skill objects from markdown files with optional YAML front matter.

    Front matter format:
        ---
        name: debugging_python
        description: How to debug Python test failures
        triggers:
          - pytest failed
          - traceback
        ---
        Content goes here...
    """

    @staticmethod
    def load_file(path: str | Path) -> Skill | None:
        """Load a single skill file. Returns None if unreadable."""
        p = Path(path)
        if not p.exists() or not p.is_file():
            return None
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            return None

        name = p.stem
        description = ""
        triggers: list[str] = []
        content = text

        # Parse YAML front matter
        front = ""
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                front = parts[1].strip()
                content = parts[2].strip()

        if front:
            try:
                meta = yaml.safe_load(front) or {}
            except yaml.YAMLError:
                meta = {}
            if isinstance(meta, dict):
                name = meta.get("name", name)
                description = meta.get("description", description)
                triggers = meta.get("triggers", triggers)
                if isinstance(triggers, str):
                    triggers = [triggers]

        return Skill(
            name=name,
            description=description,
            triggers=[t.lower() for t in triggers],
            content=content,
        )

    @staticmethod
    def load_dir(path: str | Path) -> list[Skill]:
        """Load all .md and .yaml skill files from a directory."""
        p = Path(path)
        if not p.is_dir():
            return []
        skills: list[Skill] = []
        for f in sorted(p.glob("*")):
            if f.suffix.lower() in (".md", ".yaml", ".yml"):
                skill = SkillLoader.load_file(f)
                if skill:
                    skills.append(skill)
        return skills
