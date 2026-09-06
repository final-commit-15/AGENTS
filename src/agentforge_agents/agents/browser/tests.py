"""Tests for the Browser Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.browser.agent import Agent
from agentforge_agents.agents.browser.models import BrowserRequest, BrowserResult
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.schemas.tools import ToolResult
from agentforge_agents.tools.base import BaseTool
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["browser", "http", "search"]


class _FakeBrowserTool(BaseTool):
    name = "browser"
    description = "fake browser for tests"

    def validate(self, arguments: dict) -> list[str]:
        return []

    async def execute(self, arguments: dict | None = None) -> ToolResult:
        return ToolResult.ok(self.name, {"title": "fake page", "url": (arguments or {}).get("url")})


def _make_agent() -> Agent:
    config = AgentConfig(
        id="browser",
        name="Browser Agent",
        agent_class="agentforge_agents.agents.browser.agent.Agent",
        tools=["browser", "http", "search"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="browser"),
    )
    registry = ToolRegistry()
    registry.register(_FakeBrowserTool)
    return Agent(config, tool_registry=registry)


def _request(**input_) -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="browse the homepage", input=input_)


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "browser"


@pytest.mark.asyncio
async def test_execute_missing_url_is_failed() -> None:
    agent = _make_agent()
    result = await agent.execute(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.FAILED
    assert "url" in (result.error or "")


@pytest.mark.asyncio
async def test_execute_navigate_succeeds() -> None:
    agent = _make_agent()
    result = await agent.execute(_request(url="https://example.com", operation="navigate"))
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert result.output["operation"] == "navigate"


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


def test_models_build() -> None:
    req = BrowserRequest(url="https://example.com")
    assert req.operation == "navigate"
    resp = BrowserResult(operation="navigate", output={"ok": True})
    assert resp.success is True
