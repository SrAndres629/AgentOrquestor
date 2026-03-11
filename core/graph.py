import json
from typing import Literal, Dict, Any, List
from core.state import AgentState
from core.arbitrator import arbitrator
from core.shredder import shredder
from sandbox.manager import sandbox_manager
from core.telemetry import telemetry

async def debate_node(state: AgentState) -> AgentState:
    """
    Nodo de Supervisión Dialéctica.
    Analiza estabilidad semántica y destila contexto.
    """
    pro_report = state.proponent_report
    adv_report = state.adversary_audit

    if not pro_report or not adv_report:
        telemetry.info("⚠️ Debate: Faltan reportes para realizar el arbitraje.")
        state.is_stable = False
        return state

    # 1. Ejecutar Arbitraje Espectral
    score = arbitrator.calculate_convergence(pro_report, adv_report)
    state.consensus_score = score
    state.is_stable = arbitrator.is_stable()
    
    # 2. Persistencia en historial para el Shredder
    round_data = {"proponent": pro_report, "adversary": adv_report}
    state.history.append(json.dumps(round_data))
    
    # 3. Destilación metabólica si hay inestabilidad
    if not state.is_stable:
        history_dicts = [json.loads(r) for r in state.history]
        state.dtg_context["distilled_history"] = shredder.distill(history_dicts)
        telemetry.info("🧹 Shredder: Contexto destilado para la siguiente ronda.")

    state.dtg_context["debate_rounds"] = state.dtg_context.get("debate_rounds", 0) + 1
    telemetry.info(f"📊 Estado del Debate: Ronda {state.dtg_context['debate_rounds']}, Estable: {state.is_stable}")
    return state

async def sandbox_node(state: AgentState) -> AgentState:
    """
    Nodo de Validación Empírica (Sandbox).
    Prueba el código consensuado bajo condiciones de estrés.
    """
    code_to_test = state.proponent_report
    
    # Extracción de bloque de código Python
    if "```python" in code_to_test:
        code_to_test = code_to_test.split("```python")[1].split("```")[0]

    telemetry.info("🧪 Sandbox: Iniciando prueba de estrés de la solución...")
    
    # Ejecución aislada
    validation_result = sandbox_manager.run_validation(code_to_test)
    state.dtg_context["sandbox_result"] = validation_result
    
    if validation_result["status"] == "SUCCESS":
        telemetry.info("✅ Sandbox: Validación exitosa. Código operativo.")
        state.is_stable = True
    else:
        telemetry.warning(f"❌ Sandbox: Fallo detectado. Error: {validation_result['stderr'][:100]}")
        # Inyectar el error en la próxima crítica
        state.is_stable = False 

    return state

def routing_logic(state: AgentState) -> Literal["swarm", "sandbox", "end"]:
    """
    Lógica de enrutamiento multidinámica OSAA v4.0.
    """
    # 1. Si no hay estabilidad semántica, re-debatir
    if not state.is_stable and state.dtg_context.get("debate_rounds", 0) < 3:
        if "sandbox_result" in state.dtg_context:
            telemetry.info("🔄 Re-enrutando: El error del Sandbox es la nueva Antítesis.")
        return "swarm"
    
    # 2. Si hay consenso pero no se ha validado empíricamente, ir al Sandbox
    if state.is_stable and "sandbox_result" not in state.dtg_context:
        return "sandbox"
        
    # 3. Finalización por éxito o agotamiento de cuota
    return "end"
