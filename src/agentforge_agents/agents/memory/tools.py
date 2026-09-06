"""Tools granted to the Memory Agent."""

from __future__ import annotations

from agentforge_agents.tools.fs import FilesystemTool
from agentforge_agents.tools.vector_db import VectorDBTool

MEMORY_TOOLS: list[type] = [VectorDBTool, FilesystemTool]


def get_tools() -> list[type]:
    return list(MEMORY_TOOLS)


__all__ = ["MEMORY_TOOLS", "get_tools"]
