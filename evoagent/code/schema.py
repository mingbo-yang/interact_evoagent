"""Code Agent schemas — PatchPlan and FileEdit."""

from pydantic import BaseModel, Field


class FileEdit(BaseModel):
    """A single file edit in a patch plan."""
    path: str = Field(..., description="File path relative to workspace.")
    old_text: str = Field(..., description="Exact text to find.")
    new_text: str = Field(..., description="Replacement text.")
    explanation: str = Field(default="", description="Why this edit is needed.")


class PatchPlan(BaseModel):
    """LLM-generated patch plan for fixing a bug."""
    reasoning: str = Field(default="", description="Analysis of the bug.")
    target_files: list[str] = Field(default_factory=list, description="Files that need changes.")
    edits: list[FileEdit] = Field(default_factory=list, description="Ordered list of edits.")
    test_commands: list[str] = Field(default_factory=list, description="Test commands to run after edits.")
    risk_level: str = Field(default="low", description="low, medium, or high.")
