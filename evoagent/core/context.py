"""AgentContext — the assembled context injected into each LLM call."""

from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.message import Message
from evoagent.memory.schema import MemoryItem


class AgentContext(BaseModel):
    """The full context assembled before each agent reasoning step.

    Includes the task, system prompt, conversation history,
    retrieved memories, retrieved documents, available tools,
    and loaded skills.
    """

    task: str = Field(default="", description="The current task description.")
    system_prompt: str = Field(default="", description="System prompt for the LLM.")
    messages: list[Message] = Field(
        default_factory=list,
        description="Conversation history.",
    )
    retrieved_memories: list[MemoryItem] = Field(
        default_factory=list,
        description="Memories retrieved for this context.",
    )
    retrieved_documents: list[str] = Field(
        default_factory=list,
        description="Document snippets retrieved via RAG.",
    )
    available_tools: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Function-calling schemas for available tools.",
    )
    skills: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Available skill definitions.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata.",
    )
