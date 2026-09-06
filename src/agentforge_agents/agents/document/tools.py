"""Tools granted to the Document Agent."""

from __future__ import annotations

from agentforge_agents.tools.fs import FilesystemTool
from agentforge_agents.tools.media import ImageTool, PDFTool

DOCUMENT_TOOLS: list[type] = [PDFTool, ImageTool, FilesystemTool]


def get_tools() -> list[type]:
    return list(DOCUMENT_TOOLS)


__all__ = ["DOCUMENT_TOOLS", "get_tools"]
