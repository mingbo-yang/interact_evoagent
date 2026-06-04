"""Sandbox schema — PermissionMode, PermissionDecision, PermissionRule, SandboxResult."""

from enum import StrEnum

from pydantic import BaseModel, Field


class PermissionMode(StrEnum):
    REVIEW = "review"
    AUTO = "auto"
    YOLO = "yolo"


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class PermissionRule(BaseModel):
    """A single permission rule matching actions by pattern.

    Supports three match types:
    - exact: pattern must match the target exactly
    - glob: fnmatch glob pattern (default, backward compatible)
    - regex: Python regex pattern
    """

    action_type: str = Field(
        ...,
        description="Action category: file_read, file_write, shell, python, git, tool.",
    )
    pattern: str = Field(
        ...,
        description="Pattern to match. Use '*' as wildcard for glob, or regex if match_type='regex'.",
    )
    match_type: str = Field(
        default="glob",
        description="Match type: exact, glob, or regex.",
    )
    decision: PermissionDecision = Field(
        ...,
        description="The decision when this rule matches.",
    )
    description: str = Field(default="", description="Human-readable explanation.")
    risk_level: str | None = Field(
        default=None,
        description="Optional risk level: low, medium, high.",
    )


class PolicyConfig(BaseModel):
    """Configuration for permission policy rules."""

    mode: PermissionMode = Field(
        default=PermissionMode.AUTO,
        description="Default permission mode.",
    )
    deny: list[PermissionRule] = Field(default_factory=list)
    ask: list[PermissionRule] = Field(default_factory=list)
    allow: list[PermissionRule] = Field(default_factory=list)


class SandboxResult(BaseModel):
    """Result from a sandbox execution."""

    success: bool = Field(..., description="Whether the execution succeeded.")
    stdout: str = Field(default="", description="Standard output.")
    stderr: str = Field(default="", description="Standard error.")
    exit_code: int = Field(default=0, description="Process exit code.")
    duration_ms: int = Field(default=0, description="Execution duration in milliseconds.")
    command: str = Field(default="", description="The command that was executed.")
    cwd: str | None = Field(default=None, description="Working directory.")
    metadata: dict = Field(default_factory=dict)
