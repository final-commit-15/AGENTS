"""Tools granted to the Browser Agent."""

from __future__ import annotations

from agentforge_agents.tools.browser import BrowserTool
from agentforge_agents.tools.http import HTTPTool
from agentforge_agents.tools.search import SearchTool

BROWSER_TOOLS: list[type] = [BrowserTool, HTTPTool, SearchTool]


def get_tools() -> list[type]:
    return list(BROWSER_TOOLS)


__all__ = ["BROWSER_TOOLS", "get_tools"]
