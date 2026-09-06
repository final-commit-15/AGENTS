"""I/O models for the Research Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchQuery(BaseModel):
    query: str = Field(min_length=1)
    max_sources: int = Field(default=5, ge=1)


class ResearchReport(BaseModel):
    query: str
    summary: str
    citations: list[str] = Field(default_factory=list)
    sources: int = 0


__all__ = ["ResearchQuery", "ResearchReport"]
