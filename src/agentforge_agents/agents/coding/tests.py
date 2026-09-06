"""Tests for the Coding Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.coding.agent import Agent
from agentforge_agents.agents.coding.models import CodeRequest, CodeResponse
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = [
    "filesystem",
    "terminal",
    "python_runner",
    "git",
    "docker",
    "sql",
    "github",
    "search",
    "http",
]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="coding",
        name="Coding Agent",
        agent_class="agentforge_agents.agents.coding.agent.Agent",
        tools=["filesystem", "terminal", "python_runner", "git", "docker", "sql", "github"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="coding"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="write a hello world", input=input_)


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "coding"
    assert plan.total_estimated_tasks == 1


@pytest.mark.asyncio
async def test_execute_with_mock_succeeds() -> None:
    agent = _make_agent()
    result = await agent.execute(_request(language="python", mode="generate"))
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "code" in result.output
    assert result.output["language"] == "python"


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
    assert agent.default_tools == _DEFAULT_TOOLS


@pytest.mark.asyncio
async def test_run_lifecycle_smoke() -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "initialize" in result.trace
    assert "cleanup" in result.trace


def test_models_build() -> None:
    req = CodeRequest(instructions="hello")
    assert req.mode == "generate"
    resp = CodeResponse(language="python", mode="generate", code="pass")
    assert resp.verification is None
