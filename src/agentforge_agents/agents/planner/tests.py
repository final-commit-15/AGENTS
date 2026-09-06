"""Tests for the Planner Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.planner.agent import Agent
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.events import EventType
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["search", "http"]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="planner",
        name="Planner Agent",
        agent_class="agentforge_agents.agents.planner.agent.Agent",
        tools=["search", "http"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="planner"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(
        task_id="task-1",
        instructions="Write a plan for building and testing a web app",
        input=input_,
    )


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert len(plan.tasks) >= 1
    assert plan.has_cycles() is False


@pytest.mark.asyncio
async def test_plan_with_agent_hint_uses_single_task() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request(agent_id="coding"))
    assert plan.total_estimated_tasks == 1
    assert plan.tasks[0].agent_id == "coding"


@pytest.mark.asyncio
async def test_execute_returns_plan_dict() -> None:
    agent = _make_agent()
    result = await agent.execute(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "tasks" in result.output
    assert result.metrics and result.metrics["tasks"] >= 1


@pytest.mark.asyncio
async def test_run_lifecycle_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "initialize" in result.trace
    assert "cleanup" in result.trace


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


@pytest.mark.asyncio
async def test_run_failure_is_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _make_agent()

    async def boom(_req: TaskRequest) -> TaskResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "execute", boom)
    result = await agent.run(_request())
    assert result.status == TaskStatus.FAILED
    assert result.error is not None


@pytest.mark.asyncio
async def test_stream_yields_progress_and_completed() -> None:
    agent = _make_agent()
    events = [event async for event in agent.stream(_request())]
    assert events[-1].type == EventType.TASK_COMPLETED
