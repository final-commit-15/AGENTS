"""Base agent abstraction and lifecycle handling."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from agentforge_agents.events.bus import EventBus
from agentforge_agents.schemas.agent import AgentConfig, AgentStatus
from agentforge_agents.schemas.events import EventType, ExecutionEvent
from agentforge_agents.schemas.memory import MemoryRecord
from agentforge_agents.schemas.planning import PlannerResponse, PlanTask
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus, ToolCall
from agentforge_agents.schemas.tools import ToolResult
from agentforge_agents.utils.errors import AgentError, ToolError
from agentforge_agents.utils.ids import new_id
from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.time import monotonic_ms, utc_now

if TYPE_CHECKING:
    from agentforge_agents.core.context import RuntimeContext
    from agentforge_agents.core.llm import BaseLLMClient, ModelResponse
    from agentforge_agents.core.telemetry import Telemetry
    from agentforge_agents.memory.manager import MemoryManager
    from agentforge_agents.tools.registry import ToolRegistry

log = get_logger(__name__)


class BaseAgent(ABC):
    """Common foundation shared by every specialised agent.

    Lifecycle
    =========

    ``initialize() -> plan() -> execute() | stream() -> cleanup()``

    Subclasses override :meth:`plan` and :meth:`execute` (and optionally
    :meth:`stream`) while reusing the injected services exposed as public
    attributes: ``registry`` (agents+tools), ``memory``, ``events``,
    ``telemetry`` and a lazily created model ``client``.
    """

    status: AgentStatus = AgentStatus.CREATED

    def __init__(
        self,
        config: AgentConfig,
        *,
        context: RuntimeContext | None = None,
        tool_registry: ToolRegistry | None = None,
        memory: MemoryManager | None = None,
        events: EventBus | None = None,
        telemetry: Telemetry | None = None,
        client: BaseLLMClient | None = None,
    ) -> None:
        from agentforge_agents.core.context import RuntimeContext
        from agentforge_agents.core.llm import LLMClientFactory
        from agentforge_agents.core.telemetry import Telemetry
        from agentforge_agents.events.bus import EventBus
        from agentforge_agents.memory.manager import MemoryManager
        from agentforge_agents.tools.registry import ToolRegistry

        self.config = config
        self.context = (
            context if context is not None else RuntimeContext(session_id=new_id("session"))
        )
        self.tool_registry: ToolRegistry = tool_registry or ToolRegistry()
        self.memory: MemoryManager = memory or MemoryManager(events=events)
        self.events: EventBus = events or EventBus()
        self.telemetry: Telemetry = telemetry or Telemetry()
        self._client: BaseLLMClient | None = client
        self._client_factory = LLMClientFactory
        self._initialized = False
        self._cleaned_up = False
        self.trace: list[str] = []

    # ------------------------------------------------------------------ props
    @property
    def agent_id(self) -> str:
        return self.config.id

    @property
    def client(self) -> BaseLLMClient:
        """Lazily-constructed LLM client for this agent."""
        if self._client is None:
            if self._cleaned_up:
                raise AgentError(f"agent {self.agent_id!r} is closed")
            self._client = self._client_factory.create(self.config.model)
        return self._client

    # ----------------------------------------------------------------- hooks
    async def initialize(self) -> None:
        """One-time async setup. Subclasses may override and call ``super()``."""
        if self._initialized:
            return
        self.status = AgentStatus.INITIALIZED
        self._initialized = True
        self.trace.append("initialize")
        self.telemetry.increment("agents.initialized")

    async def cleanup(self) -> None:
        """Release resources; safe to call repeatedly."""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self.status = AgentStatus.CLEANED_UP
        if self._client is not None:
            await self._client.close()
        self.trace.append("cleanup")

    @abstractmethod
    async def plan(self, request: TaskRequest) -> PlannerResponse:
        """Decompose a request into an execution plan for this agent."""

    @abstractmethod
    async def execute(self, request: TaskRequest) -> TaskResult:
        """Perform the actual work described by ``request``."""

    async def stream(self, request: TaskRequest) -> AsyncIterator[ExecutionEvent]:
        """Yield progress events during execution.

        The default implementation emits a single TASK_PROGRESS event wrapping
        the full result. Agents with streaming LLM support override this.
        """
        self.status = AgentStatus.STREAMING
        result = await self.execute(request)
        event = ExecutionEvent.create(
            EventType.TASK_PROGRESS,
            task_id=request.task_id,
            agent_id=self.agent_id,
            session_id=self.context.session_id,
            payload={
                "progress": 1.0,
                "result": result.model_dump() if hasattr(result, "model_dump") else result,
            },
        )
        yield event

    # ------------------------------------------------------------ lifecycle
    async def run(self, request: TaskRequest) -> TaskResult:
        """Run the full lifecycle for ``request`` and return a ``TaskResult``.

        Emits AGENT_STARTED / TASK_STARTED and terminal events, records
        telemetry, and guarantees cleanup even on failure.
        """
        started = monotonic_ms()
        self.status = AgentStatus.EXECUTING
        self.telemetry.mark_task_started()
        await self.initialize()
        await self.events.publish(
            ExecutionEvent.create(
                EventType.AGENT_STARTED,
                task_id=request.task_id,
                agent_id=self.agent_id,
                session_id=self.context.session_id,
            )
        )
        await self.events.publish(
            ExecutionEvent.create(
                EventType.TASK_STARTED, task_id=request.task_id, session_id=self.context.session_id
            )
        )
        try:
            nested = await self.execute(request)
            result = self._normalize_result(request, nested)
            if result.status in (TaskStatus.COMPLETED, TaskStatus.PENDING):
                await self.events.publish(
                    ExecutionEvent.create(
                        EventType.TASK_COMPLETED,
                        task_id=request.task_id,
                        agent_id=self.agent_id,
                        session_id=self.context.session_id,
                        payload={"summary": _summarize(result.output)},
                    )
                )
            else:
                await self.events.publish(
                    ExecutionEvent.create(
                        EventType.TASK_FAILED,
                        task_id=request.task_id,
                        agent_id=self.agent_id,
                        session_id=self.context.session_id,
                        payload={"error": result.error},
                    )
                )
            await self.memory.remember(
                MemoryRecord(
                    id=new_id("mem"),
                    namespace=self.context.namespace,
                    session_id=self.context.session_id,
                    agent_id=self.agent_id,
                    kind="task",
                    content=f"task {request.task_id} completed: {_summarize(result.output)}",
                )
            )
            self.status = AgentStatus.COMPLETED if result.ok() else AgentStatus.FAILED  # type: ignore[operator]
        except asyncio.CancelledError:
            await self.cleanup()
            raise
        except Exception as exc:  # noqa: BLE001
            self.status = AgentStatus.FAILED
            self.telemetry.record_error(
                operation=f"{self.agent_id}.execute", error=str(exc), task_id=request.task_id
            )
            result = TaskResult.failure(request.task_id, str(exc), agent_id=self.agent_id)
            await self.events.publish(
                ExecutionEvent.create(
                    EventType.TASK_FAILED,
                    task_id=request.task_id,
                    agent_id=self.agent_id,
                    session_id=self.context.session_id,
                    payload={"error": str(exc)},
                )
            )
        finally:
            duration = monotonic_ms() - started
            result.duration_ms = duration
            result.completed_at = utc_now()
            result.trace = self.trace
            self.telemetry.record_latency(f"{self.agent_id}.run", duration)
            self.telemetry.mark_task_finished()
            await self.cleanup()
        return result

    # ------------------------------------------------------- helper methods
    def _normalize_result(self, request: TaskRequest, nested: TaskResult | Any) -> TaskResult:
        if isinstance(nested, TaskResult):
            return nested
        return TaskResult.success(request.task_id, nested, agent_id=self.agent_id)

    async def _generate(self, messages: list[Any], **kwargs: Any) -> ModelResponse:
        """Call the configured model, recording tokens in telemetry."""
        response = await self.client.chat(messages, **kwargs)
        self.telemetry.record_tokens(response.prompt_tokens, response.completion_tokens)
        self.telemetry.increment("model.calls")
        await self.events.publish(
            ExecutionEvent.create(
                EventType.MODEL_CALL,
                task_id=getattr(self.context, "metadata", {}).get("task_id"),
                agent_id=self.agent_id,
                session_id=self.context.session_id,
                payload={
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                },
            )
        )
        return response

    async def _generate_text(self, messages: list[Any], **kwargs: Any) -> str:
        """Convience wrapper returning the raw assistant text."""
        response = await self._generate(messages, **kwargs)
        return response.content

    async def _call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None, **kwargs: Any
    ) -> ToolResult:
        """Execute a registered tool under the current permission context."""
        args = dict(arguments or {})
        if not self.context.allow_tool(tool_name):
            raise ToolError(
                f"tool {tool_name!r} is not permitted for agent {self.agent_id!r}",
                tool_name=tool_name,
            )
        started = monotonic_ms()
        call_id = new_id("call")
        await self.events.publish(
            ExecutionEvent.create(
                EventType.TOOL_STARTED,
                task_id=self.context.metadata.get("task_id"),
                agent_id=self.agent_id,
                session_id=self.context.session_id,
                payload={"call_id": call_id, "tool": tool_name, "arguments": args},
            )
        )
        try:
            result = await self.tool_registry.execute(
                tool_name, args, agent_id=self.agent_id, **kwargs
            )
        except Exception as exc:  # noqa: BLE001
            result = ToolResult.err(tool_name, str(exc))
        finally:
            result.duration_ms = monotonic_ms() - started
            tool_call = ToolCall(
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
                status="completed" if result.success else "failed",
                output=result.output,
                error=result.error,
                duration_ms=result.duration_ms,
            )
            self.context.metadata.setdefault("tool_calls", []).append(tool_call)
            await self.events.publish(
                ExecutionEvent.create(
                    EventType.TOOL_FINISHED,
                    task_id=self.context.metadata.get("task_id"),
                    agent_id=self.agent_id,
                    session_id=self.context.session_id,
                    payload={
                        "call_id": call_id,
                        "tool": tool_name,
                        "success": result.success,
                        "error": result.error,
                    },
                )
            )
        return result

    def _simple_plan(self, request: TaskRequest, agent_id: str) -> PlannerResponse:
        """Build a single-task plan (the default for leaf agents)."""
        return PlannerResponse(
            request_id=request.task_id,
            goal=request.instructions or request.text_input(),
            tasks=[
                PlanTask(
                    id=request.task_id,
                    agent_id=agent_id,
                    instruction=request.instructions or request.text_input(),
                    input=dict(request.input),
                )
            ],
            total_estimated_tasks=1,
        )


def _summarize(value: Any) -> str:
    text = value if isinstance(value, str) else str(value)
    return text[:200] if text else ""


__all__ = ["AgentStatus", "BaseAgent"]
