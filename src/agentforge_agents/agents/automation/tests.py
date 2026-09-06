"""Tests for the Automation Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.automation.agent import Agent
from agentforge_agents.agents.automation.models import AutomationRequest, AutomationResult
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["slack", "notion", "calendar", "email", "github", "http", "filesystem"]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="automation",
        name="Automation Agent",
        agent_class="agentforge_agents.agents.automation.agent.Agent",
        tools=["slack", "notion", "calendar", "email", "github", "http"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="automation"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="automate the monthly report", input=input_)


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "automation"


@pytest.mark.asyncio
async def test_execute_mock_returns_workflow() -> None:
    agent = _make_agent()
    result = await agent.execute(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert result.output["automation"] is True
    assert "workflow" in result.output


@pytest.mark.asyncio
async def test_execute_unknown_target_with_llm_mock_falls_back() -> None:
    agent = _make_agent()
    result = await agent.execute(_request(target="nope"))
    assert result.status == TaskStatus.COMPLETED


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


@pytest.mark.asyncio
async def test_run_lifecycle_smoke() -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "cleanup" in result.trace


def test_models_build() -> None:
    req = AutomationRequest(task="send digest")
    assert req.task == "send digest"
    resp = AutomationResult(automation=True, workflow="x")
    assert resp.target is None
