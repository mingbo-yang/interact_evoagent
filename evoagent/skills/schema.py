"""Skill schema."""

from pydantic import BaseModel, Field

from evoagent.core.time import utc_now_iso


class Skill(BaseModel):
    """A reusable skill that can be injected into Agent prompts.

    Skills are loaded from markdown files with YAML front matter.
    They are matched to tasks via trigger keywords.
    """

    name: str = Field(..., description="Unique skill name.")
    description: str = Field(default="", description="One-line summary.")
    triggers: list[str] = Field(default_factory=list, description="Keywords that trigger this skill.")
    content: str = Field(default="", description="The skill body (markdown text).")
    metadata: dict = Field(default_factory=dict)
    version: str = Field(default="0.1.0")
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    success_count: int = Field(default=0)
    failure_count: int = Field(default=0)
    last_used_at: str | None = Field(default=None)
