from pydantic import BaseModel
from typing import Any, Dict, Optional, List
from datetime import datetime


class AgentResult(BaseModel):
    """Result from an agent execution."""

    agent_id: str
    status: str  # "completed", "failed", "cancelled"
    output: Any
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []
    llm_calls: List[Dict[str, Any]] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = {}
    tokens_used: int = 0
    cost: Optional[float] = None