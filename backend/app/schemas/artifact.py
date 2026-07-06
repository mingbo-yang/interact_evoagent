from __future__ import annotations

from pydantic import BaseModel


class Artifact(BaseModel):
    kind: str
    title: str
    content: str

