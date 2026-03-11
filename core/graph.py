import json
from typing import Literal, Dict, Any, List
from core.state import AgentState
from core.arbitrator import arbitrator
from core.shredder import shredder
from sandbox.manager import sandbox_manager
from core.telemetry import telemetry
from core.cognitive_engine import cognitive_engine

async def heuristic_node(state: AgentState) -> AgentState:
    """
    Nodo de Pensamiento Rápido (System 1).
    Decide la estrategia y complejidad antes de gastar tokens.
    """
    strategy = cognitive_engine.apply_heuristics(state.model_dump())
    state.dtg_context["strategy"] = strategy
    
    # Inyectar estrategia en el contexto para que los agentes la lean
    telemetry.info(f"🧠 Estrategia Activada: Complejidad {strategy['complexity_level']}")
    return state

async def swarm_node(state: AgentState) -> AgentState:
    """
    Nodo de Generación Dialéctica.
    Aquí se ejecutaría la llamada real a los LLM (LeadDev y SecurityQA).
    """
    # En v4.0 esto es simulado, en v5.0 conecta con el Manager
    telemetry.info("🐝 Swarm: Ejecutando ronda de debate bajo estrategia heurística.")
    return state

async def friction_node(state: AgentState) -> AgentState:
    """
    Nodo de Validación de Antagonismo.
    Verifica si el SecurityQA realmente atacó la tesis.
    """
    pro_report = state.proponent_report
    adv_report = state.adversary_audit
    
    is_valid_friction = cognitive_engine.validate_friction(pro_report, adv_report)
    
    if not is_valid_friction:
        telemetry.warning("⚠️ Fricción: Debate inválido. Forzando re-inyección de duda.")
        state.dtg_context["friction_penalty"] = True
        state.is_stable = False
    else:
        state.dtg_context["friction_penalty"] = False
        
    return state

async def debate_node(state: AgentState) -> AgentState:
    """Nodo de Supervisión Dialéctica (Árbitro)."""
    # Si falló la fricción, no tiene sentido arbitrar
    if state.dtg_context.get("friction_penalty"):
        return state

    pro_report = state.proponent_report
    adv_report = state.adversary_audit

    score = arbitrator.calculate_convergence(pro_report, adv_report)
    state.consensus_score = score
    state.is_stable = arbitrator.is_stable()
    
    # Persistencia y Destilación
    round_data = {"proponent": pro_report, "adversary": adv_report}
    state.history.append(json.dumps(round_data))
    
    if not state.is_stable:
        history_dicts = [json.loads(r) for r in state.history]
        state.dtg_context["distilled_history"] = shredder.distill(history_dicts)
        telemetry.info("🧹 Contexto destilado para la siguiente ronda.")

    state.dtg_context["debate_rounds"] = state.dtg_context.get("debate_rounds", 0) + 1
    return state

async def sandbox_node(state: AgentState) -> AgentState:
    """Nodo de Validación Empírica (Sandbox)."""
    code_to_test = state.proponent_report
    if "```python" in code_to_test:
        code_to_test = code_to_test.split("```python")[1].split("```")[0]

    telemetry.info("🧪 Sandbox: Iniciando prueba de estrés...")
    validation_result = sandbox_manager.run_validation(code_to_test)
    state.dtg_context["sandbox_result"] = validation_result
    
    if validation_result["status"] == "SUCCESS":
        telemetry.info("✅ Sandbox: Éxito. Código operativo.")
        state.is_stable = True
    else:
        telemetry.warning(f"❌ Sandbox: Fallo. Error: {validation_result['stderr'][:100]}")
        state.is_stable = False 

    return state

def routing_logic(state: AgentState) -> Literal["swarm", "sandbox", "end"]:
    # 1. Si falló la fricción o no hay estabilidad, volver al Swarm
    if not state.is_stable and state.dtg_context.get("debate_rounds", 0) < 3:
        return "swarm"
    
    # 2. Si hay estabilidad y fricción válida, ir al Sandbox
    if state.is_stable and "sandbox_result" not in state.dtg_context:
        return "sandbox"
        
    return "end"
