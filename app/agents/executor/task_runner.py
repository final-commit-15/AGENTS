import asyncio
import logging
from typing import Optional, Dict, Any

from app.agents.registry.registry import AgentRegistry
from app.agents.base.result import AgentResult
from app.agents.base.exceptions import AgentError

logger = logging.getLogger(__name__)


class TaskRunner:
    """
    Runs a single task with retry logic, timeout, and error handling.
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    async def run_task(
        self,
        task_id: str,
        agent_id: str,
        input_data: Dict[str, Any],
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3
    ) -> AgentResult:
        """Execute a single task with retries."""
        try:
            # Get agent class and config
            agent_class = self.registry.get_agent_class(agent_id)
            config = self.registry.get_config(agent_id)

            # Instantiate agent
            agent = agent_class(config)

            # Set context
            if hasattr(agent, 'context'):
                agent.context.user_id = user_id
                agent.context.workflow_id = workflow_id
                agent.context.task_id = task_id

            # Execute with timeout from config
            result = await agent.run(
                input_data=input_data,
                timeout=config.timeout_seconds
            )
            return result

        except Exception as e:
            if retry_count < max_retries:
                wait = config.retry_delay_seconds * (2 ** retry_count)  # exponential backoff
                logger.warning(f"Task {task_id} failed, retrying in {wait}s (attempt {retry_count+1}/{max_retries})")
                await asyncio.sleep(wait)
                return await self.run_task(
                    task_id, agent_id, input_data,
                    user_id, workflow_id, execution_id,
                    retry_count + 1, max_retries
                )
            else:
                logger.error(f"Task {task_id} failed after {max_retries} retries.")
                raise AgentError(f"Max retries exceeded for task {task_id}") from e