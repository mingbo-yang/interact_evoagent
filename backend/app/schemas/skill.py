from __future__ import annotations

from pydantic import BaseModel, Field


class SkillRecord(BaseModel):
    skill_id: str
    skill_name: str
    trigger: str
    steps: list[str] = Field(default_factory=list)
    source_memories: list[str] = Field(default_factory=list)
    created_at: str

