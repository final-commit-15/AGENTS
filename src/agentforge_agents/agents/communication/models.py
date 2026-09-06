"""I/O models for the Communication Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    channel: str = "general"
    recipient: str | None = None
    subject: str = ""
    body: str = Field(default="", min_length=1)


class MessageDispatchResult(BaseModel):
    channel: str
    sent: bool
    message_id: str | None = None


__all__ = ["MessageDispatchResult", "MessageRequest"]
