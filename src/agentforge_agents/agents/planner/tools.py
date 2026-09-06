"""Tools granted to the Planner agent."""

from __future__ import annotations

from agentforge_agents.tools.http import HTTPTool
from agentforge_agents.tools.search import SearchTool

PLANNER_TOOLS: list[type] = [SearchTool, HTTPTool]

__all__ = ["PLANNER_TOOLS"]
