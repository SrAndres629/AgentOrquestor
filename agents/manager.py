"""
AgentOrquestor - Swarm Manager
==============================
Puente de integración entre LangGraph y el enjambre de AutoGen.
Inyecta telemetría de hardware, gestiona presupuestos de tokens y extrae 
el estado final tras el debate del enjambre.
"""

import json
from typing import Dict, Any, List
from core.state import AgentState
from .factory import create_swarm_manager, architect, developer, security_qa

async def run_agent_swarm(state: AgentState) -> AgentState:
    """
    Ejecuta el ciclo de debate del enjambre de agentes y actualiza el estado global.
    Utiliza el patrón de inyección de contexto desde AgentState hacia el chat de AutoGen.
    """
    
    # 1. Preparación del contexto (Inyección de Telemetría y Presupuesto)
    telemetry_data = state.hardware_telemetry
    manifest = state.task_manifest
    
    context_payload = {
        "objective": manifest.objective,
        "kpis": manifest.kpis,
        "token_budget": manifest.token_budget,
        "hardware_context": {
            "vram_free_mb": 6144 - telemetry_data.get("vram_usage_mb", 0),
            "cpu_temp_c": telemetry_data.get("i9_temperature_c", 0),
            "io_latency_ms": telemetry_data.get("io_uring_latency_ms", 0)
        },
        "dtg_context": state.dtg_context
    }
    
    # 2. Inicialización del Enjambre (Manager)
    manager = create_swarm_manager()
    
    # 3. Disparo del Debate (Inyectamos el contexto como el mensaje inicial del usuario)
    # Simulamos que el SystemArchitect recibe la instrucción directa del orquestador central.
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
    for msg in reversed(manager.groupchat.messages):
        if "APPROVED" in msg["content"] or "refactored_code" in msg["content"]:
            # Aquí aplicaríamos una extracción Regex o lógica DSPy para obtener el código limpio.
            final_patch = msg["content"]
            break
            
    # 5. Actualización del Estado
    # Simulamos la deducción del parche final
    state.dtg_context["last_swarm_resolution"] = final_patch
    
    # Descontamos tokens (Mock de presupuesto)
    state.task_manifest.token_budget -= 500 # Valor estimado del debate
    
    # Registramos el acceso al workspace
    state.workspace_paths_accessed.append("agents/manager.py")
    
    return state
