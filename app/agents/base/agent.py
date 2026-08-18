"""
Base agent implementation for AgentForge.

Defines the abstract BaseAgent class that all agents must extend.
Handles lifecycle management, timeouts, cancellation, error handling,
and structured result generation.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import AgentConfig
from .context import AgentContext
from .exceptions import AgentError, AgentTimeoutError, AgentCancelledError
from .result import AgentResult

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in AgentForge.

    Provides a standard execution lifecycle:
        created -> queued -> running -> completed / failed / cancelled

    Subclasses must implement the `execute()` method, which contains
    the agent's core logic. The `run()` method wraps it with timeouts,
    retries (via external runner), and status tracking.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the agent with its configuration.

        Args:
            config: AgentConfig instance containing identity, capabilities,
                   tool permissions, and runtime parameters.
        """
        self.id = config.id or str(uuid.uuid4())
        self.config = config
        self.context: Optional[AgentContext] = None
        self._started_at: Optional[datetime] = None
        self._status: str = "created"
        self._cancelled: bool = False

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Core execution logic to be implemented by subclasses.

        This method should contain the agent's specific behavior, including
        tool calls, LLM interactions, and any processing.

        Args:
            input_data: Dictionary containing task-specific inputs.

        Returns:
            AgentResult containing output, metadata, and execution details.
        """
        pass

    async def run(
        self,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> AgentResult:
        """
        Executes the agent with full lifecycle management.

        - Sets up context and status.
        - Applies timeout if provided (uses config timeout as fallback).
        - Handles cancellation, errors, and result packaging.

        Args:
            input_data: Input for the agent.
            timeout: Max seconds allowed for execution. If None, uses
                     config.timeout_seconds.

        Returns:
            AgentResult with execution details.

        Raises:
            AgentTimeoutError: If execution exceeds the timeout.
            AgentCancelledError: If execution is cancelled externally.
            AgentError: For any other execution failure.
        """
        self._status = "queued"
        self.context = AgentContext(inputs=input_data)
        self._started_at = datetime.now(timezone.utc)
        effective_timeout = timeout or self.config.timeout_seconds

        try:
            self._status = "running"
            logger.info(
                f"Agent {self.id} started",
                extra={"agent_id": self.id, "task": input_data}
            )

            # Run with timeout
            try:
                result = await asyncio.wait_for(
                    self.execute(input_data),
                    timeout=effective_timeout
                )
            except asyncio.TimeoutError as exc:
                self._status = "failed"
                raise AgentTimeoutError(
                    f"Agent {self.id} timed out after {effective_timeout}s"
                ) from exc

            # Package successful result
            result.agent_id = self.id
            result.status = "completed"
            result.started_at = self._started_at
            result.completed_at = datetime.now(timezone.utc)
            if result.duration_seconds is None:
                result.duration_seconds = (
                    result.completed_at - self._started_at
                ).total_seconds()
            self._status = "completed"
            return result

        except AgentCancelledError:
            self._status = "cancelled"
            logger.warning(f"Agent {self.id} cancelled")
            raise
        except Exception as exc:
            self._status = "failed"
            logger.error(
                f"Agent {self.id} failed: {exc}",
                exc_info=True,
                extra={"agent_id": self.id}
            )
            raise AgentError(f"Agent execution failed: {exc}") from exc
        finally:
            # Emit lifecycle event (can be extended)
            logger.debug(
                f"Agent {self.id} finished with status {self._status}",
                extra={"agent_id": self.id, "status": self._status}
            )

    def cancel(self) -> None:
        """
        Signal the agent to cancel its execution.

        This sets a cancellation flag; the `execute()` method should
        periodically check `self._cancelled` and raise `AgentCancelledError`
        if needed.
        """
        self._cancelled = True
        self._status = "cancelling"
        logger.info(f"Agent {self.id} cancellation requested")

    @property
    def status(self) -> str:
        """Current execution status (created, queued, running, completed, etc.)."""
        return self._status

    @property
    def is_cancelled(self) -> bool:
        """Returns True if cancellation has been requested."""
        return self._cancelled