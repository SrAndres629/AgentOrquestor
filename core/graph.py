"""
AgentOrquestor - Master Workflow Graph (LangGraph)
==================================================
Unifica la Capa 0 (Caché), Capa 1 (AutoGen Swarm) y el Sandbox de Seguridad.
Implementa persistencia cíclica, recolección de basura (GC) y logging con io_uring.
"""

import gc
import json
import asyncio
from typing import Literal, Dict, Any, List

from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.persistence import memory

# Importación de nodos de otros módulos
from core.router import get_semantic_match
from agents.manager import run_agent_swarm
from sandbox.manager import secure_eval

# --- 1. MIDDLEWARE: IO_URING LOGGING (SIMULADO ASYNC 2026) ---
async def log_telemetry_io_uring(state: AgentState, node_name: str):
    """
    Persiste los logs de la sesión en disco de forma asíncrona sin bloqueo (E/S io_uring).
    """
    log_entry = {
        "timestamp": "2026-03-10",
        "node": node_name,
        "telemetry": state.hardware_telemetry,
        "objective_preview": state.task_manifest.objective[:30]
    }
    # En producción, esto usaría liburing para inyectar directamente en el ring del kernel
    try:
        with open("docs/telemetry.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

# --- 2. DEFINICIÓN DE NODOS ---

async def router_node(state: AgentState) -> AgentState:
    """Nodo inicial: Intenta resolver vía Caché Semántica."""
    await log_telemetry_io_uring(state, "router")
    
    intent = state.task_manifest.objective
    cached_match = get_semantic_match(intent, threshold=0.98) # Muy estricto
    
    if cached_match:
        state.dtg_context["cache_hit"] = True
        state.dtg_context["last_swarm_resolution"] = cached_match["diff_patch"]
    
    # Liberar memoria tras el embedding del router
    gc.collect()
    return state

async def swarm_node(state: AgentState) -> AgentState:
    """Nodo del Enjambre: Despierta a AutoGen (SystemArchitect, LeadDeveloper, SecurityQA)."""
    await log_telemetry_io_uring(state, "swarm")
    
    # Ejecución del debate de agentes (Bridge agents/manager.py)
    new_state = await run_agent_swarm(state)
    
    gc.collect() # Importante: AutoGen puede ser pesado en RAM
    return new_state

async def sandbox_node(state: AgentState) -> AgentState:
    """Nodo de Validación: Pipeline Bandit -> Z3 -> Wasm."""
    await log_telemetry_io_uring(state, "sandbox")
    
    code = state.dtg_context.get("last_swarm_resolution", "")
    report = await secure_eval(code, state)
    
    state.dtg_context["sandbox_report"] = report
    
    # Manejo de reintentos
    if report["overall_status"] != "APPROVED":
        state.dtg_context["retry_count"] = state.dtg_context.get("retry_count", 0) + 1
    
    return state

async def human_review_node(state: AgentState) -> AgentState:
    """Nodo de Interrupción: Pausa el grafo para revisión crítica."""
    await log_telemetry_io_uring(state, "human_review")
    # Este nodo no hace nada por sí solo, LangGraph pausará antes de entrar aquí
    # si se configura como un interrupt point.
    return state

# --- 3. BORDES CONDICIONALES ---

def should_continue(state: AgentState) -> Literal["swarm", "human_review", "end"]:
    """Determina el siguiente paso basado en el reporte del sandbox."""
    report = state.dtg_context.get("sandbox_report", {})
    
    if report.get("overall_status") == "APPROVED":
        # Si el cambio es crítico (Ej: Toca archivos de sistema), pedimos aprobación
        if state.human_approval_required:
            return "human_review"
        return "end"
    
    # Si falla, pero tenemos reintentos disponibles (Máximo 3)
    retries = state.dtg_context.get("retry_count", 0)
    if retries < 3:
        return "swarm"
    
    return "end" # Aborta tras 3 fallos

# --- 4. CONSTRUCCIÓN DEL WORKFLOW ---

workflow = StateGraph(AgentState)

# Agregar Nodos
workflow.add_node("router", router_node)
workflow.add_node("swarm", swarm_node)
workflow.add_node("sandbox", sandbox_node)
workflow.add_node("human_review", human_review_node)

# Definir Flujo
workflow.set_entry_point("router")

# Lógica condicional tras el router
workflow.add_conditional_edges(
    "router",
    lambda x: "sandbox" if x.dtg_context.get("cache_hit") else "swarm"
)

# Flujo Swarm -> Sandbox
workflow.add_edge("swarm", "sandbox")

# Lógica de salida del Sandbox (Bucle de autocorrección o fin)
workflow.add_conditional_edges(
    "sandbox",
    should_continue,
    {
        "swarm": "swarm",
        "human_review": "human_review",
        "end": END
    }
)

# El humano revisa y termina
workflow.add_edge("human_review", END)

# --- 5. COMPILACIÓN CON PERSISTENCIA ---

# Compilamos el grafo con el checkpointer de SQLite (memory)
# El IDE Antigravity pausará el grafo antes del nodo 'human_review' automáticamente.
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_review"]
)
