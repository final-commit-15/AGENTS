"""I/O models for the Document Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentRequest(BaseModel):
    operation: str = "generate"
    format: str = "markdown"
    content: str = Field(default="")
    path: str | None = None


class DocumentResult(BaseModel):
    operation: str
    format: str
    path: str | None = None
    bytes_written: int = 0


__all__ = ["DocumentRequest", "DocumentResult"]
