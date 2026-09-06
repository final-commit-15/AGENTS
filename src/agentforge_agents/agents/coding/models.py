"""I/O models for the Coding Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CodeRequest(BaseModel):
    language: str = "python"
    mode: str = "generate"
    instructions: str = Field(default="", min_length=1)


class CodeResponse(BaseModel):
    language: str
    mode: str
    code: str
    verification: dict | None = None


__all__ = ["CodeRequest", "CodeResponse"]
