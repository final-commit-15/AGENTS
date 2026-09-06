"""Tools granted to the Workflow Agent."""

from __future__ import annotations

from agentforge_agents.tools.fs import FilesystemTool
from agentforge_agents.tools.http import HTTPTool
from agentforge_agents.tools.python_runner import PythonRunnerTool

WORKFLOW_TOOLS: list[type] = [HTTPTool, PythonRunnerTool, FilesystemTool]


def get_tools() -> list[type]:
    return list(WORKFLOW_TOOLS)


__all__ = ["WORKFLOW_TOOLS", "get_tools"]
