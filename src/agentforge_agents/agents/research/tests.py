"""Tests for the Research Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.research.agent import Agent
from agentforge_agents.agents.research.models import ResearchQuery, ResearchReport
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry


def _make_agent() -> Agent:
    config = AgentConfig(
        id="research",
        name="Research Agent",
        agent_class="agentforge_agents.agents.research.agent.Agent",
        tools=["search", "http"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="research"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request() -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="research quantum computing")


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "research"


@pytest.mark.asyncio
async def test_execute_with_mock_succeeds() -> None:
    agent = _make_agent()
    result = await agent.execute(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "summary" in result.output
    assert result.output["query"] == "research quantum computing"


@pytest.mark.asyncio
async def test_execute_failure_path_is_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _make_agent()

    async def boom(_request: TaskRequest) -> TaskResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "execute", boom)
    result = await agent.run(_request())
    assert result.status == TaskStatus.FAILED
    assert result.error is not None


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == ["search", "http", "filesystem", "vector_db"]


@pytest.mark.asyncio
async def test_run_lifecycle_smoke() -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert result.status == TaskStatus.COMPLETED
    assert "initialize" in result.trace


def test_models_build() -> None:
    req = ResearchQuery(query="llms")
    assert req.max_sources == 5
    report = ResearchReport(query="llms", summary="done", citations=["https://example.com"])
    assert len(report.citations) == 1
