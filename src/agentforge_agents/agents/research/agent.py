"""Research Agent - web research, citations, multi-source summaries."""

from __future__ import annotations

from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.common import Message
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Gathers and synthesizes information with provenance and citations."""

    @property
    def default_tools(self) -> list[str]:
        return ["search", "http", "filesystem", "vector_db"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "research")

    async def execute(self, request: TaskRequest) -> TaskResult:
        query = request.instructions or request.text_input()
        if self.config.model.provider == "mock":
            return TaskResult.success(
                request.task_id,
                {"query": query, "results": [], "summary": _mock_summary(query), "citations": []},
                agent_id=self.agent_id,
            )
        messages = [
            Message.system(self.config.system_prompt or "You are the Research Agent."),
            Message.user("Research the following and produce a cited report:\n" + query),
        ]
        report = await self._generate_text(messages)
        return TaskResult.success(
            request.task_id,
            {"query": query, "report": report, "citations": _extract_citations(report)},
            agent_id=self.agent_id,
        )

    async def run_search(self, queries: list[str], *, limit: int = 5) -> list[dict[str, Any]]:
        """Directly execute web searches via the search tool."""
        results: list[dict[str, Any]] = []
        for query in queries:
            result = await self._call_tool("search", {"query": query, "max_results": limit})
            if result.success and isinstance(result.output, dict):
                results.extend(result.output.get("results", []))
        return results


def _mock_summary(query: str) -> str:
    return f"Mock research summary for: {query[:200]}"


def _extract_citations(report: str) -> list[str]:
    import re

    urls = re.findall(r"https?://[^\s)\]]+", report)
    return list(dict.fromkeys(urls))


__all__ = ["Agent"]
