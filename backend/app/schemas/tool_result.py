from __future__ import annotations

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    summary: str
    modified_files: list[str] = Field(default_factory=list)
    diff: str | None = None
    test_command: str | None = None
    test_result: str | None = None
    logs: list[str] = Field(default_factory=list)
    error: str | None = None

