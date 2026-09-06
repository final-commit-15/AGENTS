"""Shared primitive types used across schemas and modules."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    """The speaker of a single conversational message."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A single chat message in a conversation exchange."""

    model_config = ConfigDict(extra="forbid")

    role: Role = Field(description="Message speaker role.")
    content: str = Field(description="Message body.")
    name: str | None = Field(default=None, description="Optional sender name.")

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        return cls(role=Role.ASSISTANT, content=content)

    def to_openai(self) -> dict[str, str]:
        """Convert to an OpenAI-compatible message dictionary."""
        return {"role": self.role.value, "content": self.content}


class LinkType(StrEnum):
    """The kind of relationship an agent may declare to another entity."""

    DEPENDS_ON = "depends_on"
    CONFLICTS_WITH = "conflicts_with"
    FOLLOWS = "follows"
