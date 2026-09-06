"""Vector database tool exposing semantic search over a shared vector store."""

from __future__ import annotations

from typing import Any, ClassVar

from agentforge_agents.memory.vector import InMemoryVectorStore, VectorMemory
from agentforge_agents.schemas.memory import MemoryRecord
from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool
from agentforge_agents.utils.ids import new_id

_OPERATIONS: set[str] = {"upsert", "search", "delete", "stats"}


class VectorDBTool(BaseTool):
    """Semantic store operations used by the Memory and Data agents.

    Wraps the framework's :class:`VectorMemory` so tool calls and agent memory
    share state when a common store instance is injected.
    """

    name: str = "vector_db"
    description: str = (
        "Upsert documents with embeddings, search by query, delete, and report stats."
    )
    category: str = "data"
    timeout_seconds: float = 30.0
    tags: ClassVar[list[str]] = ["vector", "memory"]
    parameters: ClassVar[list[ToolParameter]] = [
        ToolParameter(name="operation", type="string", required=True, enum=sorted(_OPERATIONS)),
        ToolParameter(name="id", type="string", required=False),
        ToolParameter(name="content", type="string", required=False),
        ToolParameter(name="query", type="string", required=False),
        ToolParameter(name="limit", type="integer", required=False, default=5),
        ToolParameter(name="namespace", type="string", required=False, default="default"),
        ToolParameter(name="metadata", type="object", required=False),
    ]

    def __init__(self, context: Any = None, *, vector_memory: VectorMemory | None = None) -> None:
        from agentforge_agents.tools.base import ToolContext

        super().__init__(context=context or ToolContext())
        self._vector_memory = vector_memory or VectorMemory(store=InMemoryVectorStore())

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        operation = arguments.get("operation")
        if operation not in _OPERATIONS:
            return ["invalid operation"]
        if operation == "upsert" and not arguments.get("content"):
            return ["upsert requires content"]
        if operation == "search" and not arguments.get("query"):
            return ["search requires a query"]
        if operation in {"upsert", "delete"} and not arguments.get("id"):
            return [f"{operation} requires id"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        operation = str(arguments["operation"])
        namespace = str(arguments.get("namespace") or "default")
        try:
            if operation == "upsert":
                record = MemoryRecord(
                    id=str(arguments["id"] or new_id("vec")),
                    namespace=namespace,
                    content=str(arguments["content"]),
                    metadata={**dict(arguments.get("metadata") or {}), "embeddable": True},
                )
                stored = await self._vector_memory.remember(record)
                return self.ok({"id": stored.id, "namespace": namespace, "embedded": True})
            if operation == "search":
                hits = await self._vector_memory.recall(
                    str(arguments["query"]),
                    limit=int(arguments.get("limit") or 5),
                    namespace=namespace,
                )
                return self.ok(
                    {
                        "hits": [
                            {
                                "id": hit.record.id,
                                "score": hit.score,
                                "content": hit.record.content,
                                "metadata": hit.record.metadata,
                            }
                            for hit in hits
                        ],
                        "count": len(hits),
                    }
                )
            if operation == "delete":
                deleted = await self._vector_memory.forget(str(arguments["id"]))
                return self.ok({"deleted": deleted})
            return self.ok({"vectors": await self._vector_memory.store.clear()})
        except Exception as exc:  # noqa: BLE001
            return self.err(f"vector_db {operation} failed: {exc}")


__all__ = ["VectorDBTool"]
