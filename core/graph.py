"""
AgentOrquestor - Reactive Workflow Graph (v2.4 - Cascada de Modelos)
====================================================================
Implementa el "Córtex de Cuotas" para la Misión Nocturna.
Inspirado en: Model Fallback Chain (AIAA).
"""

import gc
import json
import asyncio
from typing import Literal, Dict, Any, List

from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.persistence import memory
from core.event_bus import bus
from core.quota_manager import quota_manager

from core.router import get_semantic_match
from agents.manager import run_agent_swarm
from agents.factory import instantiate_squad, cleanup_squad
from sandbox.manager import secure_eval

# --- 1. LISTENERS DE EVOLUCIÓN (ULTRAGENT + QUOTA) ---

async def on_system_error(data: Dict[str, Any]):
    error_msg = data.get("error", "")
    print(f"[HEALER] Error detectado. Evaluando cuota y diagnóstico...")
    # Enviamos al gestor de cuotas para evaluar si es un 429
    await quota_manager.handle_api_error({"error": error_msg})
    # Disparar también la autocuración
    await bus.publish("HEAL_REQUESTED", data={"error_context": error_msg})

async def on_model_rotated(data: Dict[str, Any]):
    new_tier = data.get("new_tier")
    print(f"🔄 [ORCHESTRATOR] Cerebro rotado a: {new_tier}. Adaptando Swarm...")
    # Limpiamos VRAM para asegurar que el nuevo modelo entra limpio
    gc.collect()

async def on_hibernate(data: Dict[str, Any]):
    print("💤 [ORCHESTRATOR] SISTEMA EN HIBERNACIÓN. Cuotas agotadas. Grabando checkpoint...")
    # Aquí se guardaría el estado persistente en disco y se cerraría el daemon
    pass

# Suscripciones iniciales
bus.subscribe("SYSTEM_ERROR_DETECTED", on_system_error)
bus.subscribe("MODEL_ROTATED", on_model_rotated)
bus.subscribe("SYSTEM_HIBERNATE", on_hibernate)

# --- 2. NODOS REACTIVOS ---

async def router_node(state: AgentState) -> AgentState:
    intent = state.task_manifest.objective
    await bus.publish("TASK_RECEIVED", payload={"task": intent})
    cached_match = get_semantic_match(intent, threshold=0.98)
    if cached_match:
        state.dtg_context["cache_hit"] = True
        state.dtg_context["last_swarm_resolution"] = cached_match["diff_patch"]
    return state

async def swarm_node(state: AgentState) -> AgentState:
    """Nodo Enjambre con Resiliencia de Cuota."""
    # El swarm ahora usará el tier actual definido en quota_manager
    # state.llm_config = get_llm_config_for_tier(quota_manager.current_tier)
    new_state = await run_agent_swarm(state)
    return new_state

async def sandbox_node(state: AgentState) -> AgentState:
    code = state.dtg_context.get("last_swarm_resolution", "")
    report = await secure_eval(code, state)
    state.dtg_context["sandbox_report"] = report
    if report["overall_status"] != "APPROVED":
        state.dtg_context["retry_count"] = state.dtg_context.get("retry_count", 0) + 1
        await bus.publish("TEST_FAILED", payload={"report": report})
    return state

workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("swarm", swarm_node)
workflow.add_node("sandbox", sandbox_node)
workflow.set_entry_point("router")
workflow.add_conditional_edges("router", lambda x: "sandbox" if x.dtg_context.get("cache_hit") else "swarm")
workflow.add_edge("swarm", "sandbox")
workflow.add_conditional_edges("sandbox", lambda x: "swarm" if x.dtg_context.get("retry_count", 0) < 3 and x.dtg_context.get("sandbox_report", {}).get("overall_status") != "APPROVED" else END)

app = workflow.compile(checkpointer=memory)