"""Tests for the Communication Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.communication.agent import Agent
from agentforge_agents.agents.communication.models import MessageDispatchResult, MessageRequest
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["email", "slack", "notion", "calendar", "http"]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="communication",
        name="Communication Agent",
        agent_class="agentforge_agents.agents.communication.agent.Agent",
        tools=["email", "slack", "notion", "calendar", "http"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="communication"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(
        task_id="task-1", instructions="compose a status update for the team", input=input_
    )


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "communication"


@pytest.mark.asyncio
async def test_execute_compose_mock_returns_draft() -> None:
    agent = _make_agent()
    result = await agent.execute(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "draft" in result.output


@pytest.mark.asyncio
async def test_run_lifecycle_smoke() -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "cleanup" in result.trace


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


def test_models_build() -> None:
    req = MessageRequest(body="hi")
    assert req.channel == "general"
    resp = MessageDispatchResult(channel="slack", sent=True)
    assert resp.message_id is None
