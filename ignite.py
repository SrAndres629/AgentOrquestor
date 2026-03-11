import sys
import asyncio
from core.state import AgentState
from core.bootstrapper import bootstrapper
from core.perception import perception
from core.graph import heuristic_node, swarm_node, friction_node, debate_node, sandbox_node, routing_logic
from core.telemetry import telemetry

async def execute_mission(goal: str):
    telemetry.info(f"🚀 [IGNITE] Iniciando Misión OSAA v5.0: {goal}")
    
    # --- NIVEL COGNITIVO 0: PERCEPCIÓN ---
    situational_context = perception.analyze_situation(goal)
    
    # --- NIVEL COGNITIVO 1: BOOTSTRAPPING ---
    manifest = await bootstrapper.plan_mission(goal)
    
    # Inicializar Estado con el contexto de percepción
    state = AgentState(
        mission_goal=goal,
        dtg_context={
            "mission_id": manifest["mission_id"], 
            "mode": manifest["mode"],
            "perception": situational_context
        }
    )

    # Iniciar ciclo de vida
    state = await heuristic_node(state)
    
    for _ in range(3):
        state = await swarm_node(state)
        state = await friction_node(state)
        state = await debate_node(state)
        
        next_step = routing_logic(state)
        if next_step == "sandbox":
            state = await sandbox_node(state)
            if state.is_stable: break
        elif next_step == "end": break
            
    telemetry.info(f"✨ Misión finalizada. Modo empleado: {situational_context['mode']}")

if __name__ == "__main__":
    order = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Optimización Core"
    asyncio.run(execute_mission(order))
