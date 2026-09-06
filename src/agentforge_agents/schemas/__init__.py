"""Pydantic schemas shared across the AgentForge platform.

All schemas are v2 Pydantic models. They are exported at the package level so
the backend and AI-services repositories can ``from agentforge_agents.schemas
import ...`` without importing implementation details.
"""

from __future__ import annotations

from agentforge_agents.schemas.agent import (
    AgentConfig,
    AgentStatus,
    MemoryConfig,
    ModelConfig,
)
from agentforge_agents.schemas.common import Message, Role
from agentforge_agents.schemas.events import EventType, ExecutionEvent
from agentforge_agents.schemas.memory import MemoryRecord, MemorySearchResult
from agentforge_agents.schemas.planning import (
    PlanDependency,
    PlannerResponse,
    PlanningStrategy,
    PlanTask,
)
from agentforge_agents.schemas.task import (
    TaskRequest,
    TaskResult,
    TaskStatus,
    ToolCall,
)
from agentforge_agents.schemas.tools import ToolMetadata, ToolSchema, ToolStatus
from agentforge_agents.schemas.workflow import (
    StepResult,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStep,
    WorkflowStepType,
)

__all__ = [
    "AgentConfig",
    "AgentStatus",
    "EventType",
    "ExecutionEvent",
    "MemoryConfig",
    "MemoryRecord",
    "MemorySearchResult",
    "Message",
    "ModelConfig",
    "PlanDependency",
    "PlanTask",
    "PlannerResponse",
    "PlanningStrategy",
    "Role",
    "StepResult",
    "TaskRequest",
    "TaskResult",
    "TaskStatus",
    "ToolCall",
    "ToolMetadata",
    "ToolSchema",
    "ToolStatus",
    "WorkflowDefinition",
    "WorkflowRun",
    "WorkflowStep",
    "WorkflowStepType",
]
