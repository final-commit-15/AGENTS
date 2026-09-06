"""Runtime context - conversation, memory, permission, and telemetry state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentforge_agents.schemas.common import Message


@dataclass(slots=True)
class RuntimeContext:
    """Mutable per-invocation state threaded through the agent lifecycle.

    A fresh :class:`RuntimeContext` is constructed for every task. Agents may
    append conversation messages, check tool permissions, and read the shared
    memory namespace through this object.
    """

    session_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    namespace: str = "default"
    conversation: list[Message] = field(default_factory=list)
    tool_permissions: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Message) -> None:
        """Append a conversation message, keeping a bounded history window."""
        self.conversation.append(message)
        if len(self.conversation) > 200:
            # Drop oldest non-system message to bound memory footprint.
            for index, existing in enumerate(self.conversation):
                if existing.role.value != "system":
                    del self.conversation[index]
                    break

    def messages(self, *, include_system: bool = True) -> list[Message]:
        """Snapshot of the conversation history."""
        if include_system:
            return list(self.conversation)
        return [m for m in self.conversation if m.role.value != "system"]

    def set_telemetry(self, **values: Any) -> None:
        self.telemetry.update(values)

    def allow_tool(self, tool_name: str) -> bool:
        """Consult the permission allowlist, defaulting to permissive."""
        allowlist = self.tool_permissions.get("allow")
        denylist = self.tool_permissions.get("deny") or []
        if tool_name in denylist:
            return False
        if allowlist:
            return tool_name in allowlist
        return self.tool_permissions.get("enabled", True)

    def with_session(self, session_id: str) -> RuntimeContext:
        """Return a shallow copy targeting a new session (for delegation)."""
        import copy

        clone = copy.copy(self)
        clone.session_id = session_id
        clone.conversation = []
        return clone


__all__ = ["RuntimeContext"]
