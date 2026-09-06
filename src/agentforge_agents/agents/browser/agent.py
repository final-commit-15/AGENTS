"""Browser Agent - website navigation, form filling, screenshots, downloads."""

from __future__ import annotations

from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Drives browser operations via the browser tool."""

    @property
    def default_tools(self) -> list[str]:
        return ["browser", "http", "search"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "browser")

    async def execute(self, request: TaskRequest) -> TaskResult:
        url = request.input.get("url") if request.input else None
        operation = request.input.get("operation", "navigate") if request.input else "navigate"
        if not url:
            return TaskResult.failure(
                request.task_id, "browser operation requires a url", agent_id=self.agent_id
            )

        args: dict[str, Any] = {"operation": operation, "url": url}
        if request.input:
            if request.input.get("selector"):
                args["selector"] = request.input["selector"]
            if request.input.get("viewport"):
                args["viewport"] = request.input["viewport"]
        result = await self._call_tool("browser", args)
        return TaskResult(
            task_id=request.task_id,
            agent_id=self.agent_id,
            output={"operation": operation, "result": result.output},
            status="completed" if result.success else "failed",
            error=result.error,
        )


__all__ = ["Agent"]
