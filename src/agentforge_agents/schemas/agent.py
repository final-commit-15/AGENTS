"""Agent configuration and status schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentforge_agents.schemas.common import Message


class AgentStatus(StrEnum):
    """Lifecycle state of a loaded agent."""

    CREATED = "created"
    INITIALIZED = "initialized"
    PLANNING = "planning"
    EXECUTING = "executing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    CLEANED_UP = "cleaned_up"
    FAILED = "failed"


class ModelConfig(BaseModel):
    """Configuration of the language model an agent talks to."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="openai", description="Provider name: openai | ollama | mock.")
    name: str = Field(default="gpt-4o-mini", description="Model identifier.")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    api_key: str | None = Field(default=None, description="Provider API key (masked in exports).")
    base_url: str | None = Field(default=None, description="Override provider base URL.")
    timeout_seconds: float = Field(default=60.0, gt=0.0)

    def masked(self) -> ModelConfig:
        """Return a copy with any API key masked for logging."""
        data = self.model_dump()
        if data.get("api_key"):
            data["api_key"] = "***"
        return ModelConfig(**data)


class MemoryConfig(BaseModel):
    """Memory settings attached to an agent."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    namespace: str = Field(default="default", min_length=1)
    ttl_seconds: int = Field(default=86400, ge=0)
    session_isolation: bool = True
    embeddable: bool = Field(
        default=False, description="Whether records are embedded for retrieval."
    )


class AgentConfig(BaseModel):
    """Static configuration of a single agent."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique agent identifier, e.g. ``coding``.")
    name: str = Field(description="Human readable agent name.")
    description: str = Field(default="", description="Short capability summary.")
    version: str = Field(default="1.0.0")
    agent_class: str = Field(description="Dotted path to the BaseAgent subclass.")
    model: ModelConfig = Field(default_factory=ModelConfig)
    enabled: bool = True
    max_iterations: int = Field(default=10, gt=0)
    timeout_seconds: float = Field(default=120.0, gt=0.0)
    max_retries: int = Field(default=2, ge=0)
    tools: list[str] = Field(
        default_factory=list, description="Allowed tool names (empty = all permitted)."
    )
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    system_prompt: str | None = Field(
        default=None, description="Inline system prompt; overrides package prompt.md."
    )
    temperature: float | None = Field(
        default=None, description="Convenience override of ``model.temperature``."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_is_slug(cls, value: str) -> str:
        if not value.replace("-", "").isalnum():
            raise ValueError("agent id must be a slug")
        return value.lower()

    def apply_overrides(self, overrides: dict[str, Any]) -> AgentConfig:
        """Return a new config with scalar ``overrides`` applied (e.g. from env)."""
        data = self.model_dump()
        if "model" in overrides:
            data["model"] = ModelConfig(**{**data["model"], **overrides["model"]})
            overrides.pop("model")
        data.update(overrides)
        return AgentConfig(**data)

    def effective_system_prompt(self, package_prompt: str | None) -> str | None:
        """The inline system prompt, or the packaged ``prompt.md``, or None."""
        if self.system_prompt is not None:
            return self.system_prompt
        if package_prompt is not None and package_prompt.strip():
            return package_prompt
        return None


AgentConfig.model_rebuild()


def build_agent_config(
    *,
    agent_id: str,
    name: str | None = None,
    description: str = "",
    tools: list[str] | None = None,
    **extra: Any,
) -> AgentConfig:
    """Convenience factory for constructing an ``AgentConfig`` programmatically."""
    return AgentConfig(
        id=agent_id,
        name=name or agent_id,
        description=description,
        agent_class="agentforge_agents.core.base.BaseAgent",
        tools=tools or [],
        **extra,
    )


__all__ = [
    "AgentConfig",
    "AgentStatus",
    "MemoryConfig",
    "Message",
    "ModelConfig",
    "build_agent_config",
]
