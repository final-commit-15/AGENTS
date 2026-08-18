"""
Automation Agent – performs repetitive tasks and API interactions.
"""

import logging
from typing import Any, Dict

from app.agents.base.agent import BaseAgent
from app.agents.base.result import AgentResult

logger = logging.getLogger(__name__)


class AutomationAgent(BaseAgent):
    """
    Agent specialised in automating workflows and system tasks.

    It can send emails, interact with APIs, manage files, and schedule jobs.
    """

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute an automation task.

        Expected input keys:
            - action (str): The action to perform (e.g., "send_email", "api_call").
            - parameters (dict): Parameters for the action.

        Returns:
            AgentResult with action result.
        """
        logger.info(f"AutomationAgent executing with input: {input_data}")

        action = input_data.get("action", "noop")
        params = input_data.get("parameters", {})

        # Simulate automation (replace with actual integrations)
        if action == "send_email":
            to = params.get("to", "admin@example.com")
            subject = params.get("subject", "Automated Report")
            output = f"Email sent to {to} with subject '{subject}'."
        elif action == "api_call":
            endpoint = params.get("endpoint", "https://api.example.com")
            output = f"API call to {endpoint} simulated with success."
        else:
            output = f"No action taken; received '{action}'."

        return AgentResult(
            agent_id=self.id,
            status="completed",
            output=output,
            metadata={"action": action}
        )