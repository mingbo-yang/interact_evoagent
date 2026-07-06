from __future__ import annotations

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = None
    mode: str = Field(default="mock", pattern="^(mock|evoagent)$")


class RunCreateResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str


class ApprovalRequest(BaseModel):
    approved: bool
    message: str | None = None

