import logging
from app.agents.executor.executor import AgentExecutor
from app.agents.workflows.workflow import Workflow

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Executes a predefined workflow."""

    def __init__(self, executor: AgentExecutor):
        self.executor = executor

    async def run(self, workflow: Workflow, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        # Convert workflow steps to a plan
        plan = []
        for step in workflow.steps:
            task = {
                "id": step.id,
                "agent_id": step.agent_id,
                "dependencies": step.depends_on,
                "input": {}  # will be resolved during execution
            }
            plan.append(task)

        # Execute plan
        result = await self.executor.execute_plan(plan)
        return result