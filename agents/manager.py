"""
AgentOrquestor - Swarm Manager
==============================
Puente de integración entre LangGraph y el enjambre de AutoGen.
Inyecta telemetría de hardware, gestiona presupuestos de tokens y extrae 
el estado final tras el debate del enjambre.
"""

import json
import hashlib
import os
from typing import Dict, Any, List
from core.state import AgentState
from core.event_bus import bus
from core.hardware import get_gpu_vram_mb
from .factory import create_swarm_manager, architect, developer, security_qa

async def run_agent_swarm(state: AgentState) -> AgentState:
    """
    Ejecuta el ciclo de debate del enjambre de agentes y actualiza el estado global.
    Utiliza el patrón de inyección de contexto desde AgentState hacia el chat de AutoGen.
    """
    
    # 1. Preparación del contexto (Inyección de Telemetría y Presupuesto)
    telemetry_data = state.hardware_telemetry
    manifest = state.task_manifest

    task_id = hashlib.sha256(str(manifest.objective).encode("utf-8")).hexdigest()[:12]

    used_mb, total_mb = get_gpu_vram_mb()
    if total_mb > 0:
        telemetry_data["vram_usage_mb"] = float(used_mb)
        telemetry_data["vram_total_mb"] = float(total_mb)
    vram_total = float(telemetry_data.get("vram_total_mb") or total_mb or 0.0)
    vram_used = float(telemetry_data.get("vram_usage_mb") or used_mb or 0.0)
    vram_free = max(vram_total - vram_used, 0.0) if vram_total > 0 else 0.0

    threshold_env = os.getenv("VRAM_THRESHOLD_MB", "").strip()
    if threshold_env:
        try:
            threshold_mb = float(threshold_env)
        except ValueError:
            threshold_mb = vram_total * 0.90 if vram_total > 0 else 0.0
    else:
        threshold_mb = vram_total * 0.90 if vram_total > 0 else 0.0

    if threshold_mb > 0 and vram_used >= threshold_mb:
        await bus.publish(
            "VRAM_THRESHOLD_REACHED",
            data={
                "vram_usage_mb": vram_used,
                "threshold_mb": threshold_mb,
                "state_data": {
                    "task_manifest": {
                        "objective": manifest.objective,
                        "kpis": getattr(manifest, "kpis", None),
                        "token_budget": getattr(manifest, "token_budget", None),
                    },
                    "dtg_context": state.dtg_context,
                },
            },
            task_id=task_id,
        )
    
    context_payload = {
        "objective": manifest.objective,
        "kpis": manifest.kpis,
        "token_budget": manifest.token_budget,
        "hardware_context": {
            "vram_used_mb": vram_used,
            "vram_total_mb": vram_total,
            "vram_free_mb": vram_free,
            "cpu_temp_c": telemetry_data.get("i9_temperature_c", 0),
            "io_latency_ms": telemetry_data.get("io_uring_latency_ms", 0)
        },
        "dtg_context": state.dtg_context
    }
    
    # 2. Inicialización del Enjambre (Manager)
    dialectic = bool(state.dtg_context.get("dialectic_mode", True))
    manager = create_swarm_manager(dialectic=dialectic)
    
    # 2.1 RUMAD: Evaluación de Redundancia de Agentes (Ahorro VRAM)
    # Si la complejidad es baja y la temperatura del i9 es alta, aplicamos Dropout.
    task_complexity = len(state.task_manifest.objective.split())
    if task_complexity < 5:
        # Excluimos al Architect para ahorrar tokens y VRAM, delegando todo al LeadDeveloper
        manager.groupchat.agents = [agent for agent in manager.groupchat.agents if agent.name != "SystemArchitect"]
    
    # 3. Disparo del Debate (Inyectamos el contexto como el mensaje inicial del usuario)
    # Simulamos que el SystemArchitect recibe la instrucción directa del orquestador central.
    if dialectic:
        initial_message = (
            f"INICIO DE DEBATE DIALÉCTICO (KT-RPS)\n"
            f"OBJETIVO: {manifest.objective}\n"
            f"CONTEXTO TÉCNICO (compacto):\n{json.dumps(context_payload)}\n\n"
            "Proponente (LeadDeveloper): propón 3 mejoras críticas y un plan mínimo de implementación.\n"
            "Adversario (SecurityQA): critica y diagnostica errores/ineficiencias; exige evidencia.\n"
            "Rondas sucesivas: ambos deben criticar el trabajo del otro explícitamente.\n"
        )
    else:
        initial_message = (
            f"INICIO DE TAREA - META: {manifest.objective}\n"
            f"CONTEXTO TÉCNICO:\n{json.dumps(context_payload, indent=2)}\n"
            "Arquitecto, por favor define la estrategia."
        )
    
    # Ejecución del chat grupal (Llamada asíncrona simulada bajo el capó de AutoGen)
    # En producción 2026, esto corre en un loop asyncio real.
    chat_result = manager.initiate_chat(
        manager,
        message=initial_message,
        clear_history=True
    )
    
    # 4. Extracción de Resultados y Actualización de AgentState
    # Buscamos el último mensaje del SecurityQA o del Developer para el parche.
    final_patch = ""
    last_proponent = ""
    last_adversary = ""
    for msg in reversed(manager.groupchat.messages):
        try:
            name = msg.get("name") or msg.get("role") or ""
            content = msg.get("content") or ""
        except Exception:
            continue

        if not last_adversary and str(name) == "SecurityQA":
            last_adversary = str(content)
        if not last_proponent and str(name) == "LeadDeveloper":
            last_proponent = str(content)

        if "APPROVED" in msg["content"] or "refactored_code" in msg["content"]:
            # Aquí aplicaríamos una extracción Regex o lógica DSPy para obtener el código limpio.
            final_patch = msg["content"]
            break
            
    # 5. Actualización del Estado
    # Simulamos la deducción del parche final
    state.dtg_context["last_swarm_resolution"] = final_patch
    if last_proponent:
        state.dtg_context["proponent_report"] = last_proponent
        await bus.publish("DIALECTIC_PROPONENT", data={"content": last_proponent[:4000]}, task_id=task_id)
    if last_adversary:
        state.dtg_context["adversary_audit"] = last_adversary
        await bus.publish("DIALECTIC_ADVERSARY", data={"content": last_adversary[:4000]}, task_id=task_id)
    
    # Descontamos tokens (Mock de presupuesto)
    state.task_manifest.token_budget -= 500 # Valor estimado del debate
    
    # Registramos el acceso al workspace
    state.workspace_paths_accessed.append("agents/manager.py")
    
    return state
