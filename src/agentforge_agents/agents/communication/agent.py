"""Communication Agent - email, Slack, Notion, meetings, and summaries."""

from __future__ import annotations

from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Composes and dispatches communications via connector tools."""

    @property
    def default_tools(self) -> list[str]:
        return ["email", "slack", "notion", "calendar", "http"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "communication")

    async def execute(self, request: TaskRequest) -> TaskResult:
        action = request.input.get("action", "compose") if request.input else "compose"
        channel = request.input.get("channel") if request.input else None

        if channel in {"email", "slack"}:
            return await self._dispatch(request, channel)
        if action == "compose" and self.config.model.provider == "mock":
            return TaskResult.success(
                request.task_id,
                {
                    "draft": _mock_message(
                        request.instructions or request.text_input(), channel or "general"
                    )
                },
                agent_id=self.agent_id,
            )
        from agentforge_agents.schemas.common import Message

        messages = [
            Message.system(self.config.system_prompt or "You are the Communication Agent."),
            Message.user(
                "Compose a communication (channel: %s):\n%s"
                % (channel or "general", request.instructions or request.text_input())
            ),
        ]
        draft = await self._generate_text(messages)
        return TaskResult.success(
            request.task_id,
            {"draft": draft, "channel": channel or "general"},
            agent_id=self.agent_id,
        )

    async def _dispatch(self, request: TaskRequest, channel: str) -> TaskResult:
        if channel == "email":
            args: dict[str, Any] = {
                "to": request.input.get("to", "") if request.input else "",
                "subject": request.input.get("subject", "") if request.input else "",
                "body": (request.input.get("body") if request.input else None)
                or (request.instructions or ""),
            }
        else:
            args = {
                "operation": "post_message",
                "channel": (request.input.get("channel") if request.input else "general")
                or "general",
                "text": (request.input.get("text") if request.input else None)
                or (request.instructions or ""),
            }
        result = await self._call_tool(channel, args)
        return TaskResult(
            task_id=request.task_id,
            agent_id=self.agent_id,
            output={"channel": channel, "result": result.output},
            status="completed" if result.success else "failed",
            error=result.error,
        )


def _mock_message(task: str, channel: str) -> str:
    return f"[{channel}] {task[:200]}"


__all__ = ["Agent"]
