"""
AgentOrquestor - Reactive Workflow Graph (v2.5 - Vanguardia)
==========================================================
Implementa:
- El Hipocampo (Chronicler)
- El Metabolismo (Shredder)
- El Córtex Prefrontal (CoVe)
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
from core.chronicler import chronicler
from core.shredder import shredder

from core.router import get_semantic_match
from agents.manager import run_agent_swarm
from agents.factory import instantiate_squad, cleanup_squad
from sandbox.manager import secure_eval

# --- 1. LISTENERS DE EVOLUCIÓN (Vanguardia) ---

async def on_code_implemented(data: Dict[str, Any]):
    """Almacena la solución exitosa en la memoria episódica."""
    await chronicler.log_success(data)

async def on_vram_alert(data: Dict[str, Any]):
    print("[SENTINEL] VRAM ALERTA Crítica. Forzando Purga...")
    gc.collect()

# Suscripciones
bus.subscribe("CODE_IMPLEMENTED", on_code_implemented)
bus.subscribe("VRAM_THRESHOLD_REACHED", on_vram_alert)

# --- 2. NODOS REACTIVOS ---

async def router_node(state: AgentState) -> AgentState:
    intent = state.task_manifest.objective
    await bus.publish("TASK_RECEIVED", payload={"task": intent})
    
    # Consulta al Hipocampo (Chronicler) antes de proponer nada
    past_solutions = chronicler.query(intent)
    if past_solutions:
        print(f"📖 [ROUTER] Memoria recuperada: {len(past_solutions)} experiencias previas.")
        state.dtg_context["past_experience"] = past_solutions
        
    cached_match = get_semantic_match(intent, threshold=0.98)
    if cached_match:
        state.dtg_context["cache_hit"] = True
        state.dtg_context["last_swarm_resolution"] = cached_match["diff_patch"]
    
    return state

async def swarm_node(state: AgentState) -> AgentState:
    """Nodo Enjambre con Poda Semántica (Shredder)."""
    # 1. Aplicamos el Metabolismo: Poda del historial
    await shredder.shred(state)
    
    # 2. Inferencia del Swarm con CoVe e incentivos de costo
    new_state = await run_agent_swarm(state)
    return new_state

async def sandbox_node(state: AgentState) -> AgentState:
    code = state.dtg_context.get("last_swarm_resolution", "")
    report = await secure_eval(code, state)
    state.dtg_context["sandbox_report"] = report
    
    if report["overall_status"] == "APPROVED":
        # Notificar éxito para que el Chronicler aprenda
        await bus.publish("CODE_IMPLEMENTED", data={
            "task": state.task_manifest.objective,
            "solution": code
        })
    elif state.dtg_context.get("retry_count", 0) < 3:
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