"""
Tool permission management.

Defines which agents are allowed to call which tools.
"""

from typing import Dict, Set, Optional


class ToolPermissions:
    """
    Simple in‑memory permission store.

    Associates each agent ID with a set of tool names it is allowed to use.
    """

    def __init__(self):
        self._permissions: Dict[str, Set[str]] = {}

    def allow(self, agent_id: str, tool_name: str) -> None:
        """
        Grant an agent permission to use a specific tool.

        Args:
            agent_id: Unique identifier of the agent.
            tool_name: Name of the tool.
        """
        if agent_id not in self._permissions:
            self._permissions[agent_id] = set()
        self._permissions[agent_id].add(tool_name)

    def deny(self, agent_id: str, tool_name: str) -> None:
        """
        Revoke permission for an agent to use a tool.

        Args:
            agent_id: Unique identifier of the agent.
            tool_name: Name of the tool.
        """
        if agent_id in self._permissions:
            self._permissions[agent_id].discard(tool_name)

    def is_allowed(self, agent_id: str, tool_name: str) -> bool:
        """
        Check if an agent is allowed to use a tool.

        Args:
            agent_id: Unique identifier of the agent.
            tool_name: Name of the tool.

        Returns:
            True if the agent has permission, False otherwise.
        """
        return (
            agent_id in self._permissions and
            tool_name in self._permissions[agent_id]
        )

    def get_allowed_tools(self, agent_id: str) -> Set[str]:
        """
        Get the set of tool names an agent is allowed to use.

        Args:
            agent_id: Unique identifier of the agent.

        Returns:
            Set of tool names (empty set if none are allowed).
        """
        return self._permissions.get(agent_id, set()).copy()

    def clear(self) -> None:
        """Clear all permissions."""
        self._permissions.clear()