from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    memory_id: str
    run_id: str
    task_type: str
    user_goal: str
    successful_plan: list[str] = Field(default_factory=list)
    failed_attempts: list[str] = Field(default_factory=list)
    reusable_knowledge: list[str] = Field(default_factory=list)
    created_at: str

