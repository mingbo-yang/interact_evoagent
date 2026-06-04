"""Tests for SkillLoader."""

import tempfile
from pathlib import Path

from evoagent.skills.loader import SkillLoader


def test_load_with_front_matter():
    md = """---
name: test_skill
description: A test skill
triggers:
  - debug
  - pytest
---
# Test Skill Content
This is the body.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(md)
        p = f.name
    skill = SkillLoader.load_file(p)
    assert skill is not None
    assert skill.name == "test_skill"
    assert "debug" in skill.triggers
    assert "This is the body" in skill.content
    Path(p).unlink()


def test_load_without_front_matter():
    md = "# Just a heading\nSome content here."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(md)
        p = f.name
    skill = SkillLoader.load_file(p)
    assert skill is not None
    assert skill.content == md
    # Name should be the filename stem
    Path(p).unlink()


def test_load_dir():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("---\nname: a\ndescription: First\n---\nContent A")
        (root / "b.md").write_text("---\nname: b\ndescription: Second\n---\nContent B")
        (root / "not_a_skill.txt").write_text("ignore me")
        skills = SkillLoader.load_dir(root)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"a", "b"}


def test_load_invalid_file():
    skill = SkillLoader.load_file("/nonexistent/path.md")
    assert skill is None
