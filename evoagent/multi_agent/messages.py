"""MultiAgentMessage — messages passed between agents."""

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso


class MultiAgentMessage(BaseModel):
    """A message sent between agents in a multi-agent collaboration."""

    id: str = Field(default_factory=lambda: generate_id("mam"))
    sender: str = Field(default="")
    receiver: str = Field(default="")
    content: str = Field(default="")
    role: str = Field(default="")
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
