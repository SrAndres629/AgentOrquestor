"""
AgentOrquestor - Reactive Workflow Graph (v2.3)
==============================================
Inspirado en:
- feat_sniper (Observability)
- Ultragent (Chained Healing & Log-Level Self-Awareness)
"""

import gc
import json
import asyncio
from typing import Literal, Dict, Any, List

from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.persistence import memory
from core.event_bus import bus

from core.router import get_semantic_match
from agents.manager import run_agent_swarm
from agents.factory import instantiate_squad, cleanup_squad
from sandbox.manager import secure_eval

# --- 1. LISTENERS DE EVOLUCIÓN (ULTRAGENT STYLE) ---

async def on_task_received(data: Dict[str, Any]):
    print(f"[ORCHESTRATOR] Reacting to TASK_RECEIVED: {data.get("task", "")[:30]}...")
    pass

async def on_test_failed(data: Dict[str, Any]):
    print("[HEALER] Detectado TEST_FAILED. Activando Protocolo Chained Healing...")
    pass

async def on_vram_alert(data: Dict[str, Any]):
    print("[SENTINEL] ALERTA: VRAM Crítica (RTX 3060). Forzando GC...")
    gc.collect()
    pass

async def on_system_error(data: Dict[str, Any]):
    error_msg = data.get("error")
    print(f"[HEALER] ¡Emergencia detectada! Iniciando diagnóstico de introspección...")
    print(f"[LOG] Error: {error_msg[:100]}")
    # Publicamos evento para que el System_Architect tome el mando
    await bus.publish("HEAL_REQUESTED", data={
        "severity": "CRITICAL",
        "error_context": error_msg
    })

async def on_missing_capability(data: Dict[str, Any]):
    print(f"[ORCHESTRATOR] EVOLUCIÓN: EVENT_MISSING_CAPABILITY detectado.")
    pass

# Suscripciones iniciales
bus.subscribe("TASK_RECEIVED", on_task_received)
bus.subscribe("TEST_FAILED", on_test_failed)
bus.subscribe("VRAM_THRESHOLD_REACHED", on_vram_alert)
bus.subscribe("SYSTEM_ERROR_DETECTED", on_system_error)
bus.subscribe("EVENT_MISSING_CAPABILITY", on_missing_capability)

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
    vram = state.hardware_telemetry.get("vram_usage_mb", 0.0)
    if vram > 5500:
        await bus.publish("VRAM_THRESHOLD_REACHED", payload={"usage": vram})
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