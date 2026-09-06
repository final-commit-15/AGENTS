"""Application settings loaded from environment with sensible defaults."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentForgeSettings(BaseSettings):
    """Environment-driven runtime settings.

    Prefix ``AGENTFORGE_``; for example ``AGENTFORGE_LOG_LEVEL`` sets
    ``log_level``. An optional ``.env`` file is loaded when present.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENTFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = False
    mock_llm: bool = False

    default_agent: str = "planner"
    task_timeout_seconds: float = 120.0
    task_max_retries: int = 3
    default_model: str = "openai/gpt-4o-mini"
    default_temperature: float = 0.2
    max_iterations: int = 10

    event_bus: str = "local"  # local | redis
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "agentforge_agents"

    memory_backend: str = "memory"  # memory | redis
    memory_ttl_seconds: int = 86400
    memory_default_namespace: str = "default"
    memory_session_isolation: bool = True

    embedding_provider: str = "hash"  # hash | openai | ollama
    embedding_model: str = "text-embedding-3-small"

    docker_image: str = "python:3.12-slim"
    docker_timeout_seconds: float = 120.0

    host: str = "0.0.0.0"
    port: int = 8001

    openai_api_key: str | None = Field(default=None, json_schema_extra={"env": "OPENAI_API_KEY"})
    ollama_base_url: str = "http://localhost:11434"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def get_settings() -> AgentForgeSettings:
    """Create settings (cached via lru_cache for cheap repeated access)."""
    return _settings()


@lru_cache(maxsize=1)
def _settings() -> AgentForgeSettings:
    return AgentForgeSettings()


__all__ = ["AgentForgeSettings", "get_settings"]
