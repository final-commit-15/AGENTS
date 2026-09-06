"""Celery-compatible task wrapper presenting agents as Celery-style tasks.

Agents can be called with ``delay()``-style semantics when Celery is installed;
without it a local async task queue provides the same ergonomics.
"""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from typing import Any

from agentforge_agents.schemas.agent import AgentConfig
from agentforge_agents.schemas.task import TaskRequest, TaskResult


@dataclass(slots=True)
class AgentTaskCompat:
    """Protocol-compatible task object wrapping a BaseAgent execute call."""

    agent_id: str
    name: str
    config: AgentConfig | None = None

    async def apply_async(
        self, args: tuple | None = None, kwargs: dict | None = None
    ) -> TaskResult:
        """Execute directly in the current loop (Celery-free path).

        If Celery is installed and a ``task_id`` / broker is desired, wrap with
        ``celery_app.task(shared=False)`` at integration time.
        """
        payload = dict(kwargs or {})
        request = payload.get("request")
        if request is None or not isinstance(request, TaskRequest):
            request = TaskRequest(
                task_id=payload.pop("task_id", self.agent_id),
                input=payload,
            )
        return await _run_agent(self.config or _default_config(self.agent_id), request)

    def delay(self, *args: Any, **kwargs: Any) -> asyncio.Task[TaskResult]:
        """Fire-and-forget execution; returns the asyncio task handle."""
        return asyncio.create_task(self.apply_async(args=args, kwargs=kwargs))

    def celery_bind(self, app: Any) -> Any:
        """Expose as a real Celery task bound to ``app``."""

        @app.task(name=self.name)
        def run_task(request: dict) -> dict:
            import asyncio

            task_request = TaskRequest.model_validate(request)
            return asyncio.run(
                _run_agent(self.config or _default_config(self.agent_id), task_request)
            ).model_dump(mode="json")

        return run_task


def _default_config(agent_id: str) -> AgentConfig:
    return AgentConfig(
        id=agent_id,
        name=agent_id,
        agent_class=f"agentforge_agents.agents.{agent_id}.agent.Agent",
    )


async def _run_agent(config: AgentConfig, request: TaskRequest) -> TaskResult:
    module_path, _, class_name = config.agent_class.rpartition(".")
    module = importlib.import_module(module_path)
    agent_class = getattr(module, class_name)
    agent = agent_class(config)
    return await agent.run(request)


def build_task(agent_id: str, config: AgentConfig | None = None) -> AgentTaskCompat:
    """Build a Celery-style task for an agent id."""
    return AgentTaskCompat(agent_id=agent_id, name=f"agentforge.{agent_id}", config=config)


def agent_task_factory(registry: Any) -> dict[str, AgentTaskCompat]:
    """Build one compat task per registered agent."""
    return {
        agent_id: build_task(
            agent_id, registry.get_config(agent_id) if registry.has(agent_id) else None
        )
        for agent_id in registry.list_agents()
    }


__all__ = ["AgentTaskCompat", "agent_task_factory", "build_task"]
