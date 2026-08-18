import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.agents.registry.registry import AgentRegistry
from app.agents.executor.task_runner import TaskRunner
from app.agents.executor.lifecycle import ExecutionStatus, ExecutionRecord
from app.agents.base.result import AgentResult

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Executes a plan by running tasks in dependency order.
    Supports sequential, parallel, retries, and failure handling.
    """

    def __init__(self, registry: AgentRegistry, task_runner: TaskRunner):
        self.registry = registry
        self.task_runner = task_runner
        self.execution_records: Dict[str, ExecutionRecord] = {}

    async def execute_plan(
        self,
        plan: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a list of tasks respecting dependencies.

        Args:
            plan: List of task dicts (each with 'id', 'agent_id', 'dependencies', 'input')
            user_id: For audit
            workflow_id: For grouping

        Returns:
            Dict mapping task_id -> AgentResult
        """
        execution_id = str(uuid.uuid4())
        logger.info(f"Starting execution {execution_id} with {len(plan)} tasks")

        # Build dependency graph
        task_map = {task["id"]: task for task in plan}
        completed = {}
        results = {}
        failed_tasks = set()

        # Sort tasks topologically (simple: iterate until all done)
        # We'll use a simple loop that checks dependencies each iteration
        remaining = set(task_map.keys())
        max_retries = 3

        while remaining:
            ready = []
            for task_id in remaining:
                task = task_map[task_id]
                deps = task.get("dependencies", [])
                if all(dep in completed for dep in deps):
                    ready.append(task_id)

            if not ready:
                # Deadlock or circular dependency
                raise RuntimeError(f"Circular dependency or missing tasks: {remaining}")

            # Execute ready tasks in parallel
            tasks_to_run = []
            for task_id in ready:
                task = task_map[task_id]
                agent_id = task.get("agent_id", "research_agent")
                input_data = task.get("input", {})
                tasks_to_run.append(
                    self.task_runner.run_task(
                        task_id=task_id,
                        agent_id=agent_id,
                        input_data=input_data,
                        user_id=user_id,
                        workflow_id=workflow_id,
                        execution_id=execution_id,
                        retry_count=0,
                        max_retries=max_retries
                    )
                )

            # Run concurrently
            task_results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

            # Process results
            for idx, result in enumerate(task_results):
                task_id = ready[idx]
                if isinstance(result, Exception):
                    logger.error(f"Task {task_id} failed with {result}")
                    failed_tasks.add(task_id)
                    # Mark as failed; we could stop or continue depending on policy
                    # For now, we'll mark as completed (failed) and allow others to continue
                    completed.add(task_id)
                    results[task_id] = AgentResult(
                        agent_id=task_map[task_id].get("agent_id", ""),
                        status="failed",
                        output=None,
                        error=str(result)
                    )
                else:
                    completed.add(task_id)
                    results[task_id] = result

            remaining -= completed

        # Return all results
        return {
            "execution_id": execution_id,
            "results": results,
            "failed_tasks": list(failed_tasks),
            "status": "failed" if failed_tasks else "completed"
        }