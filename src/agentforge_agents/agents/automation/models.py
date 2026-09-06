"""I/O models for the Automation Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AutomationRequest(BaseModel):
    target: str | None = None
    task: str = Field(default="", min_length=1)


class AutomationResult(BaseModel):
    automation: bool
    workflow: str
    target: str | None = None


__all__ = ["AutomationRequest", "AutomationResult"]
