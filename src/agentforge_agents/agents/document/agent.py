"""Document Agent - PDF reading, DOCX/PPT/Excel/Markdown generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Produces and inspects office documents."""

    @property
    def default_tools(self) -> list[str]:
        return ["filesystem", "pdf", "image", "audio", "http"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "document")

    async def execute(self, request: TaskRequest) -> TaskResult:
        operation = request.input.get("operation", "generate") if request.input else "generate"
        task = request.instructions or ""

        if operation == "read_pdf":
            path = request.input.get("path") if request.input else None
            if not path:
                return TaskResult.failure(
                    request.task_id, "read_pdf requires a path", agent_id=self.agent_id
                )
            result = await self._call_tool("pdf", {"path": path})
            return TaskResult(
                task_id=request.task_id,
                agent_id=self.agent_id,
                output={"operation": operation, "result": result.output},
                status="completed" if result.success else "failed",
                error=result.error,
            )

        if operation == "generate":
            fmt = request.input.get("format", "markdown") if request.input else "markdown"
            content = request.input.get("content") if request.input else task
            output_path = request.input.get("output_path") if request.input else None
            generated = await self._generate_document(fmt, content, output_path)
            return TaskResult.success(
                request.task_id, {"format": fmt, **generated}, agent_id=self.agent_id
            )

        messages = []
        if self.config.model.provider != "mock":
            from agentforge_agents.schemas.common import Message

            messages = [
                Message.system(self.config.system_prompt or "You are the Document Agent."),
                Message.user(f"Perform document operation {operation}:\n{task}"),
            ]
            draft = await self._generate_text(messages)
        else:
            draft = task or f"placeholder document for {operation}"
        return TaskResult.success(
            request.task_id, {"operation": operation, "draft": draft}, agent_id=self.agent_id
        )

    async def _generate_document(
        self, fmt: str, content: str, output_path: str | None
    ) -> dict[str, Any]:
        if fmt == "markdown":
            path = Path(output_path or f"document-{_gen_id()}.{_extension(fmt)}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"path": str(path), "bytes": len(content)}
        from agentforge_agents.utils.ids import new_id

        suffix = _extension(fmt)
        temp = Path(f"{new_id('doc')}.{suffix}")
        temp.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(content, encoding="utf-8")
        return {
            "path": str(temp),
            "bytes": temp.stat().st_size,
            "note": f"{fmt} generated as text placeholder; install office generators for rich formats",
        }


def _gen_id() -> str:
    from agentforge_agents.utils.ids import new_id

    return new_id("doc")

    async def stream(self, request: TaskRequest):
        from agentforge_agents.schemas.events import EventType, ExecutionEvent

        result = await self.execute(request)
        yield ExecutionEvent.create(
            EventType.TASK_COMPLETED,
            task_id=request.task_id,
            agent_id=self.agent_id,
            session_id=self.context.session_id,
            payload={
                "result": (
                    result.model_dump()
                    if hasattr(result, "model_dump")
                    else {"output": result.output}
                )
            },
        )


def _extension(fmt: str) -> str:
    return {
        "markdown": "md",
        "md": "md",
        "docx": "docx",
        "doc": "doc",
        "pptx": "pptx",
        "ppt": "ppt",
        "xlsx": "xlsx",
        "xls": "xls",
    }.get(fmt, "md")


__all__ = ["Agent"]
