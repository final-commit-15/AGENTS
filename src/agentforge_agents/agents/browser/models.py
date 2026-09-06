"""I/O models for the Browser Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BrowserRequest(BaseModel):
    operation: str = "navigate"
    url: str = Field(min_length=1)


class BrowserResult(BaseModel):
    operation: str
    output: dict | None = None
    success: bool = True


__all__ = ["BrowserRequest", "BrowserResult"]
