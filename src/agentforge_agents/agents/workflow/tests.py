"""Tests for the Workflow Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.workflow.agent import Agent
from agentforge_agents.agents.workflow.models import WorkflowRunResult, WorkflowStepRequest
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["filesystem", "http", "terminal", "python_runner"]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="workflow",
        name="Workflow Agent",
        agent_class="agentforge_agents.agents.workflow.agent.Agent",
        tools=["filesystem", "http"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="workflow"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="run the deployment pipeline", input=input_)


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "workflow"


@pytest.mark.asyncio
async def test_execute_runs_steps_inline() -> None:
    agent = _make_agent()
    steps = [
        {"id": "s1", "step_type": "inline", "input": {"value": 1}},
        {"id": "s2", "step_type": "delay", "delay_seconds": 0.0},
    ]
    result = await agent.execute(_request(workflow={"steps": steps}))
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert len(result.output["step_results"]) == 2


@pytest.mark.asyncio
async def test_execute_failing_step_is_failed() -> None:
    agent = _make_agent()
    steps = [{"id": "s1", "tool_name": "missing_tool", "input": {}}]
    result = await agent.execute(_request(workflow={"steps": steps}))
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.FAILED
    assert result.error is not None


@pytest.mark.asyncio
async def test_execute_generates_workflow_when_no_steps() -> None:
    agent = _make_agent()
    result = await agent.execute(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "workflow" in result.output


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


def test_models_build() -> None:
    req = WorkflowStepRequest(step_id="s1")
    assert req.input == {}
    resp = WorkflowRunResult(run_id="r1", status="completed", steps=2)
    assert resp.steps == 2


@pytest.mark.asyncio
async def test_run_lifecycle_smoke() -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "cleanup" in result.trace
