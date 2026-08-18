import logging
from typing import List, Dict, Any
from app.agents.base.agent import BaseAgent
from app.agents.registry.registry import AgentRegistry
from app.agents.planner.task_decomposer import TaskDecomposer

logger = logging.getLogger(__name__)


class Planner:
    """
    Plans execution by breaking a user request into subtasks.
    Delegates decomposition to a TaskDecomposer.
    """

    def __init__(self, registry: AgentRegistry, decomposer: TaskDecomposer):
        self.registry = registry
        self.decomposer = decomposer

    async def plan(self, request: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generate a plan: list of tasks with agent assignments and dependencies.

        Args:
            request: User's natural language request.
            context: Additional context.

        Returns:
            List of task dictionaries: {
                "id": str,
                "description": str,
                "agent_id": str,
                "dependencies": List[str],
                "input": Dict[str, Any]
            }
        """
        # Use decomposer to break down request
        tasks = await self.decomposer.decompose(request, context)

        # For each task, select appropriate agent based on capabilities
        for task in tasks:
            if "agent_id" not in task:
                # Simple heuristic: match capabilities
                task["agent_id"] = self._select_agent_for_task(task["description"])

        # Validate that all agents exist
        for task in tasks:
            if task["agent_id"] not in self.registry.list_agents():
                logger.warning(f"Agent {task['agent_id']} not found; falling back to default.")
                task["agent_id"] = "research_agent"  # fallback

        return tasks

    def _select_agent_for_task(self, description: str) -> str:
        """Simple keyword-based selection (replace with LLM-based)."""
        keywords = {
            "research": "research_agent",
            "code": "coding_agent",
            "data": "data_agent",
            "automate": "automation_agent",
            "analysis": "data_agent",
        }
        for key, agent_id in keywords.items():
            if key in description.lower():
                return agent_id
        return "research_agent"  # default