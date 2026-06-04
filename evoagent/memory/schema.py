"""Memory schema — MemoryItem and memory types."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso


class MemoryType(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    REFLECTION = "reflection"


class MemoryItem(BaseModel):
    """A single memory entry in the agent's memory system.

    Used across all memory types: working (short-term context),
    episodic (past runs), semantic (facts), procedural (skills),
    and reflection (self-evaluation insights).
    """

    id: str = Field(
        default_factory=lambda: generate_id("mem"),
        description="Unique memory ID.",
    )
    memory_type: MemoryType = Field(
        ...,
        description="Memory category: working, episodic, semantic, procedural, or reflection.",
    )
    content: str = Field(..., description="The memory content.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata (tags, source, etc.).",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score, 0.0 to 1.0.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this memory, 0.0 to 1.0.",
    )
    source_run_id: str | None = Field(
        default=None,
        description="ID of the run that produced this memory.",
    )
    created_at: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 creation timestamp.",
    )
    updated_at: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 last update timestamp.",
    )
    last_used_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp of last retrieval.",
    )
    success_count: int = Field(
        default=0,
        description="Number of times this memory led to a successful outcome.",
    )
    failure_count: int = Field(
        default=0,
        description="Number of times this memory led to a failed outcome.",
    )
