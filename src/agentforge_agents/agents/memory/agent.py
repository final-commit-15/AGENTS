"""Memory Agent - conversation, user, project memory with semantic retrieval."""

from __future__ import annotations

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.memory import MemoryRecord
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.ids import new_id
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Reads and writes memory using the injected memory manager."""

    @property
    def default_tools(self) -> list[str]:
        return ["vector_db", "filesystem", "http"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "memory")

    async def execute(self, request: TaskRequest) -> TaskResult:
        operation = request.input.get("operation", "recall") if request.input else "recall"
        if operation in {"store", "write", "remember"}:
            return await self._store(request)
        if operation in {"recall", "retrieve", "search"}:
            return await self._recall(request)
        if operation in {"forget", "delete"}:
            return await self._forget(request)
        return TaskResult.failure(
            request.task_id, f"unknown memory operation: {operation}", agent_id=self.agent_id
        )

    async def _store(self, request: TaskRequest) -> TaskResult:
        if request.input and "content" in request.input:
            content = request.input["content"]
        else:
            content = request.instructions
        if not content:
            return TaskResult.failure(
                request.task_id, "store requires content", agent_id=self.agent_id
            )
        kind = request.input.get("kind", "general") if request.input else "general"
        record = MemoryRecord(
            id=new_id("mem"),
            namespace=self.context.namespace,
            session_id=self.context.session_id,
            agent_id=self.agent_id,
            kind=kind,
            content=str(content),
            metadata={"embeddable": kind in {"user", "project", "task"}},
        )
        stored = await self.memory.remember(record)
        return TaskResult.success(
            request.task_id, {"stored": stored.id, "kind": stored.kind}, agent_id=self.agent_id
        )

    async def _recall(self, request: TaskRequest) -> TaskResult:
        if request.input and "query" in request.input:
            query = request.input["query"]
        else:
            query = request.instructions
        if not query:
            return TaskResult.failure(
                request.task_id, "recall requires a query", agent_id=self.agent_id
            )
        limit = int(request.input.get("limit", 5)) if request.input else 5
        hits = await self.memory.retrieve(
            str(query),
            limit=limit,
            namespace=self.context.namespace,
            session_id=self.context.session_id,
            kind=request.input.get("kind") if request.input else None,
        )
        return TaskResult.success(
            request.task_id,
            {
                "query": query,
                "hits": [
                    {
                        "id": hit.record.id,
                        "score": hit.score,
                        "content": hit.record.content,
                        "kind": hit.record.kind,
                    }
                    for hit in hits
                ],
                "count": len(hits),
            },
            agent_id=self.agent_id,
        )

    async def _forget(self, request: TaskRequest) -> TaskResult:
        record_id = request.input.get("id") if request.input else None
        if not record_id:
            return TaskResult.failure(
                request.task_id, "forget requires an id", agent_id=self.agent_id
            )
        deleted = await self.memory.forget(str(record_id), namespace=self.context.namespace)
        return TaskResult.success(request.task_id, {"deleted": deleted}, agent_id=self.agent_id)


__all__ = ["Agent"]
