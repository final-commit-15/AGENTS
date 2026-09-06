"""Hierarchical error types for the entire framework.

All public exceptions derive from :class:`AgentForgeError` so callers may catch
one base type while still receiving precise error semantics.
"""

from __future__ import annotations

from typing import Any


class AgentForgeError(Exception):
    """Base error type for the agent framework."""

    def __init__(
        self, message: str, *, code: str | None = None, cause: BaseException | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.cause = cause


class ConfigError(AgentForgeError):
    """Raised when configuration files are missing, malformed, or invalid."""


class SchemaValidationError(AgentForgeError):
    """Raised when a Pydantic model rejects an input."""

    def __init__(self, message: str, *, errors: list[Any] | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.errors = errors or []


class RegistryError(AgentForgeError):
    """Raised for agent or tool registration problems."""


class AgentError(AgentForgeError):
    """Raised when an agent lifecycle operation fails."""


class OrchestrationError(AgentForgeError):
    """Raised when planning, routing, or parallel execution fails."""

    def __init__(self, message: str, *, task_id: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.task_id = task_id


class ToolError(AgentForgeError):
    """Raised when a tool fails at runtime."""

    def __init__(self, message: str, *, tool_name: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.tool_name = tool_name


class PermissionDeniedError(ToolError):
    """Raised when a tool call is rejected by the permission policy."""


class MemoryError(AgentForgeError):
    """Raised for memory backend failures."""


class ExecutionError(AgentForgeError):
    """Raised by the execution engine."""


class RetryError(ExecutionError):
    """Raised when all retry attempts are exhausted."""


class TaskTimeoutError(ExecutionError):
    """Raised when a task exceeds its timeout budget."""


class TaskCancelledError(ExecutionError):
    """Raised when a task is cancelled by the lifecycle manager."""


class RateLimitError(AgentForgeError):
    """Raised when a rate limiter budget is exhausted."""


class LLMError(AgentForgeError):
    """Raised when a model call fails."""


class SandboxError(ExecutionError):
    """Raised when sandboxed code fails to run safely."""


__all__ = [
    "AgentError",
    "AgentForgeError",
    "ConfigError",
    "ExecutionError",
    "LLMError",
    "MemoryError",
    "OrchestrationError",
    "PermissionDeniedError",
    "RateLimitError",
    "RegistryError",
    "RetryError",
    "SandboxError",
    "SchemaValidationError",
    "TaskCancelledError",
    "TaskTimeoutError",
    "ToolError",
]
