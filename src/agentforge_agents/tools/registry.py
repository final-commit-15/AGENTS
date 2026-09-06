"""Central ToolRegistry - registration, introspection, and permission-gated execution."""

from __future__ import annotations

from typing import Any

from agentforge_agents.schemas.tools import ToolMetadata, ToolResult, ToolSchema
from agentforge_agents.tools.base import BaseTool, ToolContext
from agentforge_agents.tools.permission import ToolPermissions
from agentforge_agents.utils.errors import RegistryError, ToolError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class ToolRegistry:
    """Registers tool *types* once and executes them per-call with context.

    The registry is deliberately cheap: tools are lightweight (no connections),
    so constructing a fresh instance per invocation avoids shared-state bugs.
    """

    def __init__(self, permissions: ToolPermissions | None = None) -> None:
        self._tools: dict[str, type[BaseTool]] = {}
        self.permissions = permissions or ToolPermissions()

    # ------------------------------------------------------ registration
    def register(self, tool: type[BaseTool] | BaseTool) -> None:
        """Register a tool type (pass the class, not an instance)."""
        tool_type = tool if isinstance(tool, type) else type(tool)
        if not issubclass(tool_type, BaseTool):
            raise RegistryError(f"tool must subclass BaseTool: {tool_type}")
        name = tool_type.__dict__.get("name") or tool_type.__name__.lower().replace("tool", "")
        self._tools[name] = tool_type

    def register_all(self, tools: list[type[BaseTool] | BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    # ------------------------------------------------------- introspection
    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> type[BaseTool]:
        try:
            return self._tools[name]
        except KeyError:
            raise RegistryError(f"unknown tool: {name!r}") from None

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[ToolSchema]:
        return [self._build(name).schema() for name in self.names()]

    def metadata_all(self) -> list[ToolMetadata]:
        return [self._build(name).metadata() for name in self.names()]

    def json_schemas(self) -> list[dict[str, Any]]:
        return [schema.json_schema() for schema in self.schemas()]

    def _build(self, name: str, context: ToolContext | None = None) -> BaseTool:
        tool = self._tools[name](context=context)
        return tool

    # -------------------------------------------------------- execution
    async def execute(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        agent_id: str | None = None,
        context: ToolContext | None = None,
    ) -> ToolResult:
        """Run ``name`` with ``arguments`` under the registry permissions.

        Raises :class:`ToolError` on validation failure or :class:`PermissionDeniedError`
        when the permission policy rejects the call.
        """
        self.permissions.require(name, agent_id=agent_id)
        tool_context = context or ToolContext(agent_id=agent_id, permissions=self.permissions)
        tool = self._build(name, context=tool_context)
        return await tool.execute_guarded(arguments)

    async def execute_with_timeout(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        agent_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> ToolResult:
        """Execute within a hard timeout (cancels the underlying coroutine)."""
        import asyncio

        self.permissions.require(name, agent_id=agent_id)
        tool = self._build(
            name, context=ToolContext(agent_id=agent_id, permissions=self.permissions)
        )
        budget = timeout_seconds or tool.timeout_seconds
        coro = tool.execute_guarded(arguments)
        try:
            return await asyncio.wait_for(coro, timeout=budget)
        except TimeoutError as exc:
            raise ToolError(f"tool {name!r} timed out after {budget}s", tool_name=name) from exc

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ToolRegistry tools={self.names()}>"


__all__ = ["ToolRegistry"]
