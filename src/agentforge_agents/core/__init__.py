"""Core agent framework - base abstractions, registry, loading, lifecycle, telemetry."""

from __future__ import annotations

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.core.context import RuntimeContext
from agentforge_agents.core.lifecycle import LifecycleManager, TaskLifecycle
from agentforge_agents.core.llm import (
    BaseLLMClient,
    LLMClientFactory,
    MockLLMClient,
    ModelResponse,
    OllamaLLMClient,
    OpenAILLMClient,
)
from agentforge_agents.core.loader import AgentLoader
from agentforge_agents.core.registry import AgentRegistry
from agentforge_agents.core.telemetry import Telemetry

__all__ = [
    "AgentLoader",
    "AgentRegistry",
    "BaseAgent",
    "BaseLLMClient",
    "LLMClientFactory",
    "LifecycleManager",
    "MockLLMClient",
    "ModelResponse",
    "OllamaLLMClient",
    "OpenAILLMClient",
    "RuntimeContext",
    "TaskLifecycle",
    "Telemetry",
]
