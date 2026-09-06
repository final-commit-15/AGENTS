"""Tool permission policy - allow/deny lists scoped by agent and global defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentforge_agents.utils.errors import PermissionDeniedError
from agentforge_agents.utils.serialization import to_dict


@dataclass(slots=True)
class PermissionVerdict:
    """Result of a permission decision."""

    allowed: bool
    tool: str
    reason: str


@dataclass(slots=True)
class ToolPermissions:
    """Hierarchical allow/deny resolution.

    Resolution order (first match wins):
      1. deny list applicable to the caller (agent-first, then global)
      2. allow list applicable to the caller (agent-first, then global)
      3. ``default_mode`` - "deny" or "allow"

    ``None`` allow lists mean "everything allowed".
    """

    default_mode: str = "allow"
    global_allowed: set[str] | None = None
    global_denied: set[str] = field(default_factory=set)
    agent_allowed: dict[str, set[str]] = field(default_factory=dict)
    agent_denied: dict[str, set[str]] = field(default_factory=dict)
    user_denied: set[str] = field(default_factory=set)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolPermissions:
        """Build from a parsed ``permissions.yaml`` section."""
        agent_data = data.get("agents", {})
        return cls(
            default_mode=data.get("default_mode", "allow"),
            global_allowed=(
                set(data.get("global_allowed", [])) or None if data.get("global_allowed") else None
            ),
            global_denied=set(data.get("global_denied", [])),
            agent_allowed={
                name: set(cfg.get("allowed", []))
                for name, cfg in agent_data.items()
                if cfg.get("allowed")
            },
            agent_denied={name: set(cfg.get("denied", [])) for name, cfg in agent_data.items()},
            user_denied=set(data.get("user_denied", [])),
        )

    def is_allowed(
        self, tool: str, *, agent_id: str | None = None, user_id: str | None = None
    ) -> PermissionVerdict:
        if tool in self.user_denied:
            return PermissionVerdict(False, tool, "denied for user")
        if agent_id and tool in self.agent_denied.get(agent_id, set()):
            return PermissionVerdict(False, tool, f"denied for agent {agent_id}")
        if tool in self.global_denied:
            return PermissionVerdict(False, tool, "globally denied")
        if agent_id and agent_id in self.agent_allowed:
            if tool in self.agent_allowed[agent_id]:
                return PermissionVerdict(True, tool, f"allowed for agent {agent_id}")
        if self.global_allowed is not None:
            if tool in self.global_allowed:
                return PermissionVerdict(True, tool, "globally allowed")
            return PermissionVerdict(False, tool, "not in global allowlist")
        if self.default_mode == "deny":
            return PermissionVerdict(False, tool, "default deny mode")
        return PermissionVerdict(True, tool, "default allow mode")

    def require(self, tool: str, *, agent_id: str | None = None) -> None:
        verdict = self.is_allowed(tool, agent_id=agent_id)
        if not verdict.allowed:
            raise PermissionDeniedError(
                f"tool {tool!r}: {verdict.reason}",
                tool_name=tool,
            )

    def summary(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass(slots=True)
class PermissionPolicy:
    """Higher-level policy pairing a permissions table with policy metadata."""

    version: str = "1.0.0"
    permissions: ToolPermissions = field(default_factory=ToolPermissions)
    require_confirmation_for: set[str] = field(default_factory=set)
    audit: bool = True

    def to_permissions(self) -> ToolPermissions:
        return self.permissions


__all__ = ["PermissionPolicy", "PermissionVerdict", "ToolPermissions"]
