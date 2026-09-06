"""Central tool registry with all built-in tools pre-registered."""

from __future__ import annotations

import importlib
from typing import Any

from agentforge_agents.tools.base import BaseTool, ToolContext
from agentforge_agents.tools.browser import BrowserTool
from agentforge_agents.tools.docker import DockerTool
from agentforge_agents.tools.fs import FilesystemTool
from agentforge_agents.tools.git import GitTool
from agentforge_agents.tools.http import HTTPTool
from agentforge_agents.tools.media import AudioTool, ImageTool, PDFTool
from agentforge_agents.tools.permission import PermissionPolicy, ToolPermissions
from agentforge_agents.tools.python_runner import PythonRunnerTool
from agentforge_agents.tools.registry import ToolRegistry
from agentforge_agents.tools.search import SearchTool
from agentforge_agents.tools.services import (
    CalendarTool,
    EmailTool,
    GitHubTool,
    NotionTool,
    SlackTool,
)
from agentforge_agents.tools.sql import SQLTool
from agentforge_agents.tools.terminal import TerminalTool
from agentforge_agents.tools.vector_db import VectorDBTool
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)

ALL_TOOLS: list[type[BaseTool]] = [
    FilesystemTool,
    TerminalTool,
    PythonRunnerTool,
    GitTool,
    DockerTool,
    GitHubTool,
    SQLTool,
    BrowserTool,
    SearchTool,
    HTTPTool,
    CalendarTool,
    EmailTool,
    SlackTool,
    NotionTool,
    PDFTool,
    ImageTool,
    AudioTool,
    VectorDBTool,
]


def build_registry(
    *,
    permissions: ToolPermissions | None = None,
    tool_classes: list[type[BaseTool]] | None = None,
) -> ToolRegistry:
    """Create a :class:`ToolRegistry` with the built-in tools registered."""
    registry = ToolRegistry(permissions=permissions or ToolPermissions())
    for tool_class in tool_classes or ALL_TOOLS:
        registry.register(tool_class)
    return registry


def load_tool_registry_from_config(
    path: str | None = None, *, policy: PermissionPolicy | None = None
) -> ToolRegistry:
    """Build a registry honouring an optional ``tools.yaml`` / ``permissions.yaml``."""
    permissions = policy.permissions if policy is not None else ToolPermissions()
    if path:
        from agentforge_agents.utils.config import read_yaml

        data = read_yaml(path)
        if "permissions" in data:
            permissions = ToolPermissions.from_dict(data["permissions"])
        enabled = set(data.get("enabled") or [])
        if enabled:
            from agentforge_agents.tools.permission import PermissionVerdict

            original = permissions.is_allowed

            def scope_allowed(
                tool: str, *, agent_id: str | None = None, user_id: str | None = None
            ) -> PermissionVerdict:
                if tool not in enabled:
                    return PermissionVerdict(False, tool, "disabled by tools.yaml")
                return original(tool, agent_id=agent_id, user_id=user_id)

            permissions.is_allowed = scope_allowed  # type: ignore[method-assign]
    return build_registry(permissions=permissions)


def discover_tools(package: str = "agentforge_agents.tools") -> list[type[BaseTool]]:
    """Auto-discover additional tool modules providing a ``TOOLS`` list."""
    found: list[type[BaseTool]] = []
    module = importlib.import_module(package)
    for info in _iter_modules(module):
        try:
            sub = importlib.import_module(f"{package}.{info.name}")
        except Exception:  # noqa: BLE001
            continue
        declared = getattr(sub, "TOOLS", None)
        if declared:
            found.extend(t for t in declared if issubclass(t, BaseTool))
    return found


def _iter_modules(module: Any) -> list[Any]:
    import pkgutil

    return list(pkgutil.iter_modules(module.__path__))  # type: ignore[attr-defined]


__all__ = [
    "ALL_TOOLS",
    "BaseTool",
    "PermissionPolicy",
    "ToolContext",
    "ToolPermissions",
    "ToolRegistry",
    "build_registry",
    "discover_tools",
    "load_tool_registry_from_config",
]
