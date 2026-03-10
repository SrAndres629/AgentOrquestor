"""
AgentOrquestor - Reactive Workflow Graph (v2.6 - .cortex/ Vault)
==============================================================
Implementa:
- Decoupled Memory Architecture (.cortex/)
- Brain Handover (Consciousness Manifesto)
- Multimodal Indexing
"""

import sys
import gc
import json
import asyncio
import hashlib
from typing import Literal, Dict, Any, List

from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.event_bus import bus
from core.quota_manager import quota_manager
from core.memory_manager import vault
from core.shredder import shredder

from core.router import get_semantic_match
from agents.manager import run_agent_swarm
from sandbox.manager import secure_eval

# --- 1. LISTENERS DE VANGUARDIA (.cortex) ---

def _task_id_from_objective(objective: str) -> str:
    return hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12]

async def on_model_rotated(data: Dict[str, Any]):
    new_tier = data.get("new_tier")
    sys.stderr.write(f"🔄 [ORCHESTRATOR] Cerebro rotado a: {new_tier}. Adaptando conciencia...\n")
    gc.collect()

async def on_system_error(data: Dict[str, Any]):
    error_msg = data.get("error", "")
    sys.stderr.write("[HEALER] Error detectado. Evaluando cuota y diagnóstico...\n")
    # Pasamos el estado al quota_manager para el "Manifiesto de Conciencia"
    await quota_manager.handle_api_error({"error": error_msg})

async def on_vram_threshold_reached(data: Dict[str, Any]):
    used_mb = data.get("vram_usage_mb")
    threshold_mb = data.get("threshold_mb")
    state_data = data.get("state_data")
    await quota_manager.handle_vram_pressure(state_data=state_data, used_mb=used_mb, threshold_mb=threshold_mb)

# Suscripciones
bus.subscribe("MODEL_ROTATED", on_model_rotated)
bus.subscribe("SYSTEM_ERROR_DETECTED", on_system_error)
bus.subscribe("VRAM_THRESHOLD_REACHED", on_vram_threshold_reached)

# --- 2. NODOS REACTIVOS ---

async def router_node(state: AgentState) -> AgentState:
    intent = state.task_manifest.objective
    task_id = _task_id_from_objective(intent)
    await bus.publish("TASK_RECEIVED", data={"task": intent}, task_id=task_id)
    
    # 🧠 Recuperación desde la Bóveda .cortex/
    past_memory = vault.retrieve_relevant_memory(intent)
    if past_memory:
        state.dtg_context["vault_memory"] = past_memory
        sys.stderr.write("🔑 [ROUTER] Memoria recuperada desde la Bóveda .cortex/\n")
        
    cached_match = get_semantic_match(intent, threshold=0.98)
    if cached_match:
        state.dtg_context["cache_hit"] = True
        state.dtg_context["last_swarm_resolution"] = cached_match["diff_patch"]
    
    return state

async def swarm_node(state: AgentState) -> AgentState:
    """Nodo Enjambre con Poda Semántica y Recuperación de Bóveda."""
    await shredder.shred(state)
    new_state = await run_agent_swarm(state)
    return new_state

async def sandbox_node(state: AgentState) -> AgentState:
    code = state.dtg_context.get("last_swarm_resolution", "")
    report = await secure_eval(code, state)
    state.dtg_context["sandbox_report"] = report
    task_id = _task_id_from_objective(state.task_manifest.objective)
    
    if report["overall_status"] == "APPROVED":
        await bus.publish("CODE_IMPLEMENTED", data={
            "task": state.task_manifest.objective,
            "solution": code
        }, task_id=task_id)
    elif state.dtg_context.get("retry_count", 0) < 3:
        state.dtg_context["retry_count"] = state.dtg_context.get("retry_count", 0) + 1
        await bus.publish("TEST_FAILED", data={"report": report}, task_id=task_id)
    
    return state

workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("swarm", swarm_node)
workflow.add_node("sandbox", sandbox_node)
workflow.set_entry_point("router")
workflow.add_conditional_edges("router", lambda x: "sandbox" if x.dtg_context.get("cache_hit") else "swarm")
workflow.add_edge("swarm", "sandbox")
workflow.add_conditional_edges("sandbox", lambda x: "swarm" if x.dtg_context.get("retry_count", 0) < 3 and x.dtg_context.get("sandbox_report", {}).get("overall_status") != "APPROVED" else END)

app = workflow.compile()
