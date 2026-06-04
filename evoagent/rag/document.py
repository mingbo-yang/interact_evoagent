"""Document and DocumentChunk schema."""

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso


class Document(BaseModel):
    """A loaded document with metadata."""

    id: str = Field(default_factory=lambda: generate_id("doc"))
    text: str = Field(default="")
    metadata: dict = Field(default_factory=dict)
    source: str = Field(default="")
    created_at: str = Field(default_factory=utc_now_iso)


class DocumentChunk(BaseModel):
    """A chunk of a document for retrieval."""

    id: str = Field(default_factory=lambda: generate_id("chk"))
    document_id: str = Field(default="")
    text: str = Field(default="")
    start_char: int = 0
    end_char: int = 0
    metadata: dict = Field(default_factory=dict)
    score: float | None = Field(default=None)
