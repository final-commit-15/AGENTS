from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ExecutionStatus:
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    TOOL_CALL = "tool_call"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionRecord(BaseModel):
    execution_id: str
    task_id: str
    agent_id: str
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    status: str = ExecutionStatus.CREATED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None