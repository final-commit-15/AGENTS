"""
Coding Agent – generates, reviews, and refines code.
"""

import logging
from typing import Any, Dict

from app.agents.base.agent import BaseAgent
from app.agents.base.result import AgentResult

logger = logging.getLogger(__name__)


class CodingAgent(BaseAgent):
    """
    Agent specialised in programming tasks.

    It can write code from specifications, review existing code, and suggest refactorings.
    """

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute a coding task.

        Expected input keys:
            - task (str): Description of what to generate/review.
            - language (str, optional): Programming language.
            - code (str, optional): Existing code to review.

        Returns:
            AgentResult with generated code or review comments.
        """
        logger.info(f"CodingAgent executing with input: {input_data}")

        task = input_data.get("task", "")
        language = input_data.get("language", "python")
        existing_code = input_data.get("code", "")

        # Simulate LLM code generation (replace with actual LLM call)
        if "review" in task.lower():
            output = f"Code review for {language}:\n- The code is well-structured.\n- Consider adding docstrings."
        else:
            output = f"# Generated {language} code for: {task}\ndef main():\n    print('Hello, world!')"

        return AgentResult(
            agent_id=self.id,
            status="completed",
            output=output,
            metadata={"task": task, "language": language}
        )