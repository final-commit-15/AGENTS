"""BaseTool contract and the ToolContext passed to every invocation."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agentforge_agents.schemas.tools import ToolMetadata, ToolResult, ToolSchema, ToolStatus
from agentforge_agents.utils.errors import PermissionDeniedError, ToolError

MAX_ARGUMENT_BYTES = 64 * 1024


@dataclass(slots=True)
class ToolContext:
    """Per-invocation context handed to tools during execution."""

    agent_id: str | None = None
    session_id: str | None = None
    task_id: str | None = None
    permissions: Any = None
    environment: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Every tool implements execute/validate/schema/metadata and is registered once."""

    name: str = "tool"
    description: str = ""
    version: str = "1.0.0"
    category: str = "general"
    requires_credentials: bool = False
    creds_present: bool = True
    timeout_seconds: float = 30.0
    tags: list[str] = []

    def __init__(self, context: ToolContext | None = None) -> None:
        self.context = context or ToolContext()

    # ----------------------------------------------------- required surface
    @abstractmethod
    def validate(self, arguments: dict[str, Any]) -> list[str]:
        """Return a list of validation errors (empty means valid)."""

    @abstractmethod
    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Run the tool and return a :class:`ToolResult`."""

    def schema(self) -> ToolSchema:
        """Use ``parameters`` declared on the subclass if present."""
        declared = getattr(self, "parameters", [])
        return ToolSchema(name=self.name, description=self.description, parameters=declared)

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            category=self.category,
            requires_credentials=self.requires_credentials,
            credentials_present=self.creds_present,
            status=ToolStatus.READY if self.creds_present else ToolStatus.MISSING_CREDENTIALS,
            tags=list(getattr(self, "tags", [])),
            timeout_seconds=self.timeout_seconds,
        )

    # ------------------------------------------------------- helpers
    def check_permissions(self) -> None:
        """Raise :class:`PermissionDeniedError` when the context denies this tool."""
        permissions = self.context.permissions
        if (
            permissions is not None
            and not permissions.is_allowed(self.name, agent_id=self.context.agent_id).allowed
        ):
            raise PermissionDeniedError(
                f"tool {self.name!r} not permitted",
                tool_name=self.name,
            )

    def enforce_size(self, arguments: dict[str, Any] | None) -> dict[str, Any]:
        """Reject absurdly large argument payloads before further processing."""
        arguments = arguments or {}
        if len(repr(arguments)) > MAX_ARGUMENT_BYTES:
            raise ToolError(f"tool {self.name!r} arguments exceed size limit", tool_name=self.name)
        return arguments

    async def execute_guarded(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Validate + permission-check + bounded execution in one call."""
        started = time.monotonic()
        self.check_permissions()
        arguments = self.enforce_size(arguments)
        errors = self.validate(arguments)
        if errors:
            raise ToolError(
                f"tool {self.name!r} validation failed: {'; '.join(errors)}", tool_name=self.name
            )
        result = await self.execute(arguments)
        if result.duration_ms == 0:
            result.duration_ms = (time.monotonic() - started) * 1000.0
        return result

    def ok(self, output: Any, **metadata: Any) -> ToolResult:
        return ToolResult.ok(self.name, output, **metadata)

    def err(self, error: str, **metadata: Any) -> ToolResult:
        return ToolResult.err(self.name, error, **metadata)


__all__ = ["BaseTool", "ToolContext"]
