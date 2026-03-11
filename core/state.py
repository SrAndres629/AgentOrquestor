"""
AgentOrquestor - Núcleo de Estado Neuro-Simbólico (v2.1)
=================================================
Añadido: Soporte para Sentinels de Hardware (Inspirado en feat_sniper).
"""

from typing import Annotated, Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo
import os

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class SentinelStatus(BaseModel):
    """Estado de vigilancia del sistema guard."""
    vram_threshold_breached: bool = False
    cpu_thermal_alert: bool = False
    integrity_lock: bool = False

class AgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    dtg_context: Dict[str, Any] = Field(default_factory=dict)
    debate_history: List[Dict[str, str]] = Field(default_factory=list)
    consensus_score: float = 0.0
    is_stable: bool = False
    
    # 4. Telemetría Avanzada (Sentinel Mode)
    hardware_telemetry: Dict[str, Any] = Field(
        default_factory=lambda: {
            "vram_usage_mb": 0.0,
            "i9_temperature_c": 0.0,
            "io_uring_latency_ms": 0.0,
            "sentinel": SentinelStatus().dict()
        }
    )
    
    task_manifest: Any
    human_approval_required: bool = False
    workspace_paths_accessed: List[str] = Field(default_factory=list)

    @field_validator("workspace_paths_accessed")
    @classmethod
    def detect_directory_traversal(cls, paths: List[str], info: ValidationInfo) -> List[str]:
        project_root = os.path.abspath(os.getcwd())
        for path_str in paths:
            resolved_path = os.path.abspath(path_str)
            if not resolved_path.startswith(project_root):
                raise ValueError(f"Security Alert: Out of bounds access to {resolved_path}")
        return paths
