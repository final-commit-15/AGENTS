"""
Data Agent – analyses and transforms data.
"""

import logging
from typing import Any, Dict

from app.agents.base.agent import BaseAgent
from app.agents.base.result import AgentResult

logger = logging.getLogger(__name__)


class DataAgent(BaseAgent):
    """
    Agent specialised in data processing and analysis.

    It can run SQL queries, perform statistical analysis, and generate visualisations.
    """

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute a data task.

        Expected input keys:
            - query (str): SQL or natural‑language query.
            - data (list, optional): Data to analyse.
            - operation (str): e.g., "aggregate", "chart", "clean".

        Returns:
            AgentResult with analysis results.
        """
        logger.info(f"DataAgent executing with input: {input_data}")

        operation = input_data.get("operation", "describe")
        query = input_data.get("query", "")
        data = input_data.get("data", [])

        # Simulate data analysis (replace with actual engine)
        if operation == "aggregate":
            output = {"total": len(data), "average": sum(data) / len(data) if data else 0}
        elif operation == "chart":
            output = f"Chart generated for {len(data)} data points."
        else:
            output = f"Data description: {len(data)} rows, columns: [sample]"

        return AgentResult(
            agent_id=self.id,
            status="completed",
            output=output,
            metadata={"operation": operation}
        )