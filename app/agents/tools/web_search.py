"""
Web Search tool – stub implementation.
"""

import logging
from typing import List, Dict, Any

from app.agents.tools.base import BaseTool, ToolInput, ToolOutput
from pydantic import Field


class WebSearchInput(ToolInput):
    """Input schema for web search."""
    query: str = Field(..., description="Search query")
    num_results: int = Field(5, description="Number of results to return")


class WebSearchTool(BaseTool):
    """Simulated web search tool."""
    name = "web_search"
    description = "Search the web for information."
    input_schema = WebSearchInput

    async def execute(self, input_data: WebSearchInput) -> ToolOutput:
        logging.info(f"WebSearchTool: searching for '{input_data.query}'")
        # In production, call a real search API (e.g., SerpAPI)
        results = [
            {"title": f"Result {i+1} for '{input_data.query}'", "snippet": "This is a snippet."}
            for i in range(input_data.num_results)
        ]
        return ToolOutput(result=results, metadata={"query": input_data.query, "source": "stub"})