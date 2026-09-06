"""Configuration loader - reads YAML configs and builds production objects.

Central entry point that wires the settings, agent registry, tool registry,
memory, and event bus together from the bundled YAML configuration.
"""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentforge_agents.config.settings import AgentForgeSettings, get_settings
from agentforge_agents.core.loader import AgentLoader
from agentforge_agents.core.registry import AgentRegistry
from agentforge_agents.core.telemetry import Telemetry
from agentforge_agents.events.bus import EventBus
from agentforge_agents.memory.embeddings import EmbeddingFactory
from agentforge_agents.memory.manager import MemoryManager
from agentforge_agents.memory.router import MemoryPolicies, MemoryRouter
from agentforge_agents.tools.permission import PermissionPolicy, ToolPermissions
from agentforge_agents.utils.config import read_yaml
from agentforge_agents.utils.errors import ConfigError
from agentforge_agents.utils.logging import configure_logging, get_logger

log = get_logger(__name__)

_CONFIG_PACKAGE = "agentforge_agents.config.configs"


@dataclass(slots=True)
class BootstrapResult:
    """Everything needed to boot the agents service."""

    settings: AgentForgeSettings
    registry: AgentRegistry
    events: EventBus
    memory: MemoryManager
    telemetry: Telemetry
    permissions: ToolPermissions


def load_yaml_config(name: str) -> dict[str, Any]:
    """Read one bundled YAML config (e.g. ``agents.yaml``)."""
    path = Path(str(importlib.resources.files(_CONFIG_PACKAGE) / name))
    if not path.is_file():
        raise ConfigError(f"missing bundled config: {name}")
    return read_yaml(path)


def load_permissions() -> ToolPermissions:
    data = load_yaml_config("permissions.yaml")
    return ToolPermissions.from_dict(data)


def load_policy() -> PermissionPolicy:
    data = load_yaml_config("permissions.yaml")
    return PermissionPolicy(
        version=str(data.get("version", "1.0.0")),
        permissions=ToolPermissions.from_dict(data),
        require_confirmation_for=set(data.get("require_confirmation_for", [])),
        audit=bool(data.get("audit", True)),
    )


def build_telemetry() -> Telemetry:
    return Telemetry()


def build_events(settings: AgentForgeSettings | None = None) -> EventBus:
    settings = settings or get_settings()
    if settings.event_bus == "redis":
        from agentforge_agents.events.adapters.redis import RedisEventAdapter

        return EventBus(RedisEventAdapter(settings.redis_url, channel=settings.redis_prefix))
    from agentforge_agents.events.adapters.local import LocalEventAdapter

    return EventBus(LocalEventAdapter())


def build_memory(
    settings: AgentForgeSettings | None = None, *, events: EventBus | None = None
) -> MemoryManager:
    settings = settings or get_settings()
    backend = settings.memory_backend
    if backend == "redis":
        from agentforge_agents.memory.short_term import RedisMemoryBackend

        short_term = RedisMemoryBackend(settings.redis_url, prefix=settings.redis_prefix)
    else:
        from agentforge_agents.memory.short_term import InMemoryMemoryBackend

        short_term = InMemoryMemoryBackend()

    embedder = EmbeddingFactory.create(
        settings.embedding_provider,
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    from agentforge_agents.memory.vector import InMemoryVectorStore, VectorMemory

    router = MemoryRouter(
        short_term=short_term,
        long_term=VectorMemory(store=InMemoryVectorStore(), embedder=embedder),
        policies=MemoryPolicies(
            default_ttl_seconds=settings.memory_ttl_seconds,
            session_isolation=settings.memory_session_isolation,
            short_term_kinds=("conversation", "general"),
            embeddable_kinds=("user", "project", "task"),
        ),
    )
    return MemoryManager(router, events=events)


def build_registry(settings: AgentForgeSettings | None = None) -> AgentRegistry:
    """Discover and load every agent packaged in ``agents`` via their configs."""
    settings = settings or get_settings()
    loader = AgentLoader(package_source="agentforge_agents.agents")
    registry = loader.load_all()
    if settings.mock_llm:
        for config in registry.all_configs():
            config.model.provider = "mock"
    return registry


def bootstrap(*, configure__logging: bool = True) -> BootstrapResult:
    """Assemble the full runtime stack."""
    settings = get_settings()
    if configure__logging:
        configure_logging(settings.log_level, json=settings.log_json)
        log.info("logging_configured", level=settings.log_level, environment=settings.environment)

    events = build_events(settings)
    telemetry = build_telemetry()
    memory = build_memory(settings, events=events)
    permissions = load_permissions()
    registry = build_registry(settings)
    log.info("bootstrap_complete", agents=registry.list_agents(), tools=None)
    return BootstrapResult(
        settings=settings,
        registry=registry,
        events=events,
        memory=memory,
        telemetry=telemetry,
        permissions=permissions,
    )


__all__ = [
    "BootstrapResult",
    "bootstrap",
    "build_events",
    "build_memory",
    "build_registry",
    "load_policy",
    "load_yaml_config",
]
