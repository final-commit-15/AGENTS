from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime


class AgentContext(BaseModel):
    """Context for a single agent execution."""

    inputs: Dict[str, Any]
    task_id: Optional[str] = None
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation: List[Dict[str, Any]] = []
    previous_results: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    started_at: Optional[datetime] = None