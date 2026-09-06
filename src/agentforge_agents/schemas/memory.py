"""Memory record schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentforge_agents.utils.time import utc_now


class MemoryRecord(BaseModel):
    """A single stored memory entry."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique memory identifier.")
    namespace: str = Field(default="default")
    session_id: str | None = Field(default=None, description="Isolation key; None shares memory.")
    agent_id: str | None = None
    kind: str = Field(
        default="general", description="conversation | user | project | task | general"
    )
    content: str = Field(description="Memory body text.")
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = Field(default=None, description="Optional dense vector.")
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = Field(default=None, description="TTL deadline.")

    def expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or utc_now()) >= self.expires_at


class MemorySearchResult(BaseModel):
    """A scored memory hit from semantic or keyword retrieval."""

    model_config = ConfigDict(extra="forbid")

    record: MemoryRecord
    score: float = Field(ge=0.0, le=1.0)


__all__ = ["MemoryRecord", "MemorySearchResult"]
