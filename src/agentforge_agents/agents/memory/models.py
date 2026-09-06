"""I/O models for the Memory Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryEntryRequest(BaseModel):
    operation: str = "recall"
    content: str | None = None
    query: str | None = None
    kind: str = "general"


class MemoryRecallResult(BaseModel):
    hits: list[dict] = Field(default_factory=list)
    count: int = 0


__all__ = ["MemoryEntryRequest", "MemoryRecallResult"]
