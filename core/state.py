from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """Estado Soberano del OSAA v4.0."""
    mission_goal: str
    current_agent: str = 'LeadDev'
    proponent_report: str = ''
    adversary_audit: str = ''
    dtg_context: Dict[str, Any] = Field(default_factory=dict)
    consensus_score: float = 0.0
    is_stable: bool = False
    history: List[str] = Field(default_factory=list)
