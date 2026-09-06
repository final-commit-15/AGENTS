"""Tools granted to the Communication Agent."""

from __future__ import annotations

from agentforge_agents.tools.services import CalendarTool, EmailTool, NotionTool, SlackTool

COMMUNICATION_TOOLS: list[type] = [EmailTool, SlackTool, NotionTool, CalendarTool]


def get_tools() -> list[type]:
    return list(COMMUNICATION_TOOLS)


__all__ = ["COMMUNICATION_TOOLS", "get_tools"]
