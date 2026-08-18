from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class WorkflowStep(BaseModel):
    id: str
    agent_id: str
    input_map: Dict[str, str] = {}  # map from previous outputs
    depends_on: List[str] = []


class Workflow(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep]