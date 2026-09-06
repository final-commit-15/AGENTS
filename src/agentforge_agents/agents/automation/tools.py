"""Tools granted to the Automation Agent."""

from __future__ import annotations

from agentforge_agents.tools.http import HTTPTool
from agentforge_agents.tools.services import (
    CalendarTool,
    EmailTool,
    GitHubTool,
    NotionTool,
    SlackTool,
)

AUTOMATION_TOOLS: list[type] = [
    SlackTool,
    NotionTool,
    CalendarTool,
    EmailTool,
    GitHubTool,
    HTTPTool,
]


def get_tools() -> list[type]:
    return list(AUTOMATION_TOOLS)


__all__ = ["AUTOMATION_TOOLS", "get_tools"]
