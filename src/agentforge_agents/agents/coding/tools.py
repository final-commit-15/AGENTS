"""Tools granted to the Coding Agent."""

from __future__ import annotations

from agentforge_agents.tools.docker import DockerTool
from agentforge_agents.tools.fs import FilesystemTool
from agentforge_agents.tools.git import GitTool
from agentforge_agents.tools.python_runner import PythonRunnerTool
from agentforge_agents.tools.services import GitHubTool
from agentforge_agents.tools.sql import SQLTool
from agentforge_agents.tools.terminal import TerminalTool

CODING_TOOLS: list[type] = [
    FilesystemTool,
    TerminalTool,
    PythonRunnerTool,
    GitTool,
    DockerTool,
    SQLTool,
    GitHubTool,
]


def get_tools() -> list[type]:
    return list(CODING_TOOLS)


__all__ = ["CODING_TOOLS", "get_tools"]
