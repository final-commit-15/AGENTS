"""Tests for the Document Agent."""

from __future__ import annotations

import pytest

from agentforge_agents.agents.document.agent import Agent
from agentforge_agents.agents.document.models import DocumentRequest, DocumentResult
from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.tools.registry import ToolRegistry

_DEFAULT_TOOLS = ["filesystem", "pdf", "image", "audio", "http"]


def _make_agent() -> Agent:
    config = AgentConfig(
        id="document",
        name="Document Agent",
        agent_class="agentforge_agents.agents.document.agent.Agent",
        tools=["filesystem", "pdf", "image"],
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace="document"),
    )
    return Agent(config, tool_registry=ToolRegistry())


def _request(**input_) -> TaskRequest:
    return TaskRequest(task_id="task-1", instructions="generate a markdown report", input=input_)


@pytest.mark.asyncio
async def test_plan_returns_planner_response() -> None:
    agent = _make_agent()
    plan = await agent.plan(_request())
    assert isinstance(plan, PlannerResponse)
    assert plan.tasks[0].agent_id == "document"


@pytest.mark.asyncio
async def test_generate_markdown_writes_file(tmp_path) -> None:
    agent = _make_agent()
    target = tmp_path / "report.md"
    result = await agent.execute(
        _request(
            operation="generate", format="markdown", content="# Hello", output_path=str(target)
        )
    )
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "# Hello"


@pytest.mark.asyncio
async def test_read_pdf_missing_path_is_failed() -> None:
    agent = _make_agent()
    result = await agent.execute(_request(operation="read_pdf"))
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_run_lifecycle_smoke(tmp_path) -> None:
    agent = _make_agent()
    result = await agent.run(_request())
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED
    assert "cleanup" in result.trace


def test_default_tools() -> None:
    agent = _make_agent()
    assert agent.default_tools == _DEFAULT_TOOLS


def test_models_build() -> None:
    req = DocumentRequest(operation="generate")
    assert req.format == "markdown"
    resp = DocumentResult(operation="generate", format="markdown", path="a.md", bytes_written=3)
    assert resp.bytes_written == 3
