"""
AgentOrquestor - Núcleo de Estado Neuro-Simbólico
=================================================
Este módulo define the AgentState, el corazón del orquestador LangGraph.

Persistencia Wake-on-Call (Memoria <-> Reposo):
-----------------------------------------------
La persistencia de este estado se serializa directamente a SQLite (`core/database.db`) o mediante 
almacenes GraphRAG, garantizando que el grafo pueda pausarse (interrupts) y el daemon principal 
descargue los tensores del LLM y el estado semántico pesado de los 16GB de RAM unificada hacia el 
disco NVMe. Solo al re-invocarse la ejecución por el IDE (E/S io_uring) se hidrata el estado 
desde el disco, manteniendo un perfil de memoria mínimo cuando el Swarm está en reposo.
"""

from typing import Annotated, Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo
import os

# Dependencia LangChain/LangGraph (Q1-2026 Compatible)
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TaskManifest(BaseModel):
    """Manifiesto de la tarea actual y presupuesto."""
    objective: str = Field(description="Meta semántica actual del enjambre.")
    kpis: List[str] = Field(default_factory=list, description="Criterios de éxito demostrables.")
    token_budget: int = Field(default=8192, description="Presupuesto de inferencia remanente.")

    @field_validator("token_budget")
    @classmethod
    def prevent_negative_budget(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"El presupuesto de tokens no puede ser negativo (detectado: {v}).")
        return v


class MCPToolStatus(BaseModel):
    """Metadatos de integridad de herramientas bidireccionales."""
    name: str = Field(description="Identificador del servidor MCP.")
    sha256_hash: str = Field(description="Hash de integridad del plugin para Wasm sandbox.")
    is_active: bool = Field(default=True)


class AgentState(BaseModel):
    """
    Estado global del Grafo (LangGraph + Pydantic v2).
    Se utiliza como TypedDict extendido garantizando validación estricta Z3-ready.
    """
    
    # 1. Historial de debate (Annotated para reducer de LangGraph)
    messages: Annotated[List[BaseMessage], add_messages] = Field(
        default_factory=list, 
        description="Historial del orquestador y los agentes."
    )
    
    # 2. Percepción Estructural (Data Transformation Graphs)
    dtg_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Grafo de linaje de datos en memoria pre-parseado (No-AST)."
    )
    
    # 3. Compresión KV y Optimizaciones de VRAM (RTX 3060 - 6GB)
    kv_compression_ratio: float = Field(
        default=0.12, 
        ge=0.01, 
        le=1.0,
        description="Ratio de compresión asimétrica PyramidKV."
    )
    
    # 4. Telemetría de Kernel (eBPF -> io_uring)
    hardware_telemetry: Dict[str, Any] = Field(
        default_factory=lambda: {
            "vram_usage_mb": 0.0,
            "i9_temperature_c": 0.0,
            "io_uring_latency_ms": 0.0
        },
        description="Métricas instrumentales desde sensores del kernel base."
    )
    
    # 5. Objetivos y Restricciones
    task_manifest: TaskManifest
    
    # 6. Herramientas MCP
    active_mcp_tools: List[MCPToolStatus] = Field(
        default_factory=list,
        description="Herramientas habilitadas para inyección de dependencias temporales."
    )
    
    # 7. Control de Flujo (Human-in-the-Loop)
    human_approval_required: bool = Field(
        default=False,
        description="Pausa de seguridad SMT obligatoria para operaciones de Nivel 2."
    )
    
    # 8. Seguridad: Directorio de Trabajo Confinado
    workspace_paths_accessed: List[str] = Field(
        default_factory=list,
        description="Registro de archivos tocados por el modelo para sandboxing iterativo."
    )

    @field_validator("workspace_paths_accessed")
    @classmethod
    def detect_directory_traversal(cls, paths: List[str], info: ValidationInfo) -> List[str]:
        """
        Validador estricto para rutas de archivos.
        Imposibilita el Path Traversal fuera de las carpetas de trabajo del proyecto IDE.
        """
        # Obtenemos el directorio base del proyecto asumiendo ejecución desde la raíz
        project_root = os.path.abspath(os.getcwd())
        
        for path_str in paths:
            # Resolvemos cualquier '.' o '..' potencial en Wasm o llamadas locales
            resolved_path = os.path.abspath(path_str)
            
            # Verificación de confinamiento
            if not resolved_path.startswith(project_root):
                raise ValueError(
                    f"Alerta de Seguridad (Directory Traversal): El agente intentó "
                    f"acceder a una ruta restringida '{resolved_path}' fuera del "
                    f"perímetro del proyecto '{project_root}'."
                )
        return paths
