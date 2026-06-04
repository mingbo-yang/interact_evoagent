"""Skill system — registry, loading, evaluation.

Provides:
- Skill: schema for reusable skills
- SkillLoader: load from .md/.yaml files with YAML front matter
- SkillRegistry: register, search, track usage
- SkillRetriever: retrieve skills matching a task
- SkillUsageTracker: persist usage statistics
- SkillEvolution: adjust priorities based on usage

Import sub-modules lazily to avoid circular imports with schema.
"""
