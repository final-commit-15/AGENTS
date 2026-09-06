"""Automation Agent - workflow automation, scheduling, and integrations."""

from __future__ import annotations

from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.common import Message
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Designs and executes automations across Gmail, Slack, Notion, GitHub, etc."""

    @property
    def default_tools(self) -> list[str]:
        return ["slack", "notion", "calendar", "email", "github", "http", "filesystem"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "automation")

    async def execute(self, request: TaskRequest) -> TaskResult:
        task = request.instructions or request.text_input()
        target = request.input.get("target") if request.input else None
        if target in {"slack", "email", "notion", "calendar", "github"}:
            return await self._execute_integration(request, target)
        if self.config.model.provider == "mock":
            return TaskResult.success(
                request.task_id,
                {"automation": True, "task": task[:200], "workflow": _mock_workflow(task)},
                agent_id=self.agent_id,
            )
        messages = [
            Message.system(self.config.system_prompt or "You are the Automation Agent."),
            Message.user("Design an automation for this task:\n" + task),
        ]
        workflow = await self._generate_text(messages)
        return TaskResult.success(request.task_id, {"workflow": workflow}, agent_id=self.agent_id)

    async def _execute_integration(self, request: TaskRequest, target: str) -> TaskResult:
        tool_name = {
            "slack": "slack",
            "email": "email",
            "notion": "notion",
            "calendar": "calendar",
            "github": "github",
        }[target]
        args: dict[str, Any] = {}
        if target == "slack":
            args = {
                "operation": "post_message",
                "channel": request.input.get("channel", "general"),
                "text": request.input.get("text", request.instructions or ""),
            }
        elif target == "email":
            args = {
                "to": request.input.get("to", ""),
                "subject": request.input.get("subject", ""),
                "body": request.input.get("body", ""),
            }
        else:
            args = request.input.get("arguments") or {}

        result = await self._call_tool(tool_name, args)
        return TaskResult(
            task_id=request.task_id,
            agent_id=self.agent_id,
            output={"target": target, "result": result.output, "error": result.error},
            status="completed" if result.success else "failed",
            error=result.error,
        )


def _mock_workflow(task: str) -> str:
    return f"automation: trigger -> {task[:200]} -> notify"


__all__ = ["Agent"]
