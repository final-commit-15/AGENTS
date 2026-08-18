from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    id: Optional[str] = None
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)  # Tool names allowed
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout_seconds: int = 120
    retry_limit: int = 3
    retry_delay_seconds: int = 5
    metadata: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True