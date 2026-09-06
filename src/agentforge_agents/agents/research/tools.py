"""Tools granted to the Research Agent."""

from __future__ import annotations

from agentforge_agents.tools.http import HTTPTool
from agentforge_agents.tools.search import SearchTool

RESEARCH_TOOLS: list[type] = [SearchTool, HTTPTool]


def get_tools() -> list[type]:
    return list(RESEARCH_TOOLS)


__all__ = ["RESEARCH_TOOLS", "get_tools"]
