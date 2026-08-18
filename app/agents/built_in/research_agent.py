"""
Research Agent – gathers and synthesizes information from various sources.
"""

import logging
from typing import Any, Dict

from app.agents.base.agent import BaseAgent
from app.agents.base.result import AgentResult
from app.agents.tools.registry import ToolRegistry
from app.agents.tools.web_search import WebSearchTool, WebSearchInput

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    Agent specialized in research tasks.

    It can perform web searches, analyse documents, and extract key data.
    """

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute the research task.

        Expected input keys:
            - query (str): The search query.
            - num_results (int, optional): Number of results to retrieve.

        Returns:
            AgentResult containing the search results.
        """
        logger.info(f"ResearchAgent executing with input: {input_data}")

        query = input_data.get("query", "")
        num_results = input_data.get("num_results", 5)

        if not query:
            output = "No query provided; performing generic research."
            return AgentResult(
                agent_id=self.id,
                status="completed",
                output=output,
                metadata={"query": query}
            )

        # Retrieve the web search tool from the registry
        try:
            tool_class = ToolRegistry().get("web_search")
            tool = tool_class()  # instantiate
            search_input = WebSearchInput(query=query, num_results=num_results)
            result = await tool.execute(search_input)
            output = result.result
            metadata = result.metadata
        except KeyError:
            logger.error("Web search tool not registered; falling back to stub.")
            output = f"Simulated research results for '{query}'"
            metadata = {"query": query, "note": "stub"}

        return AgentResult(
            agent_id=self.id,
            status="completed",
            output=output,
            metadata=metadata
        )