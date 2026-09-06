"""Tests for the Memory Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.memory.agent import Agent
from agentforge_agents.agents.memory.models import MemoryEntryRequest, MemoryRecallResult
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["vector_db", "filesystem", "http"]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="memory",
        name="Memory Agent",
        agent_class="agentforge_agents.agents.memory.agent.Agent",
        tools=["vector_db", "filesystem", "http"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="memory"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="remember the project goal", input=input_)


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "memory"


@pytest.mark.asyncio
async def test_store_and_recall_roundtrip() -> None:
    agent = _make_agent()
    stored = await agent.execute(
        _request(operation="store", content="the project uses Python", kind="project")
    )
    assert isinstance(stored, TaskResult)
    assert stored.status == TaskStatus.COMPLETED
    recalled = await agent.execute(_request(operation="recall", query="project"))
    assert recalled.status == TaskStatus.COMPLETED
    assert recalled.output["count"] >= 1


@pytest.mark.asyncio
async def test_execute_unknown_operation_is_failed() -> None:
    agent = _make_agent()
    result = await agent.execute(_request(operation="explode"))
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_recall_without_query_is_failed() -> None:
    agent = _make_agent()
    result = await agent.execute(_request(operation="recall", query=""))
    assert result.status == TaskStatus.FAILED


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


def test_models_build() -> None:
    req = MemoryEntryRequest(query="who am i")
    assert req.kind == "general"
    resp = MemoryRecallResult(hits=[{"id": "1"}], count=1)
    assert resp.count == 1
