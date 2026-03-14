"""
AgentOrquestor — Punto de Ignición Unificado v5.0
===================================================
Conecta la orden del usuario con el SwarmLauncher distribuido.

Flujo:
  1. Recibir objetivo del usuario (CLI o import)
  2. Analizar situación (percepción)
  3. Delegar al SwarmLauncher (actor model distribuido)

Ya NO usa el grafo monolítico (graph.py). La ejecución ocurre
en terminales tmux aisladas orquestadas por swarm_launcher.py.
"""

import sys
import asyncio
from core.telemetry import telemetry
from core.perception import perception
from core.swarm_launcher import SwarmLauncher


async def execute_mission(goal: str, mode: str = "DIALECTIC"):
    """
    Punto de entrada principal del enjambre distribuido.
    
    Args:
        goal: Objetivo de la misión en lenguaje natural.
        mode: DIALECTIC | EFFICIENCY | FULL_SWARM.
              Se auto-degrada a EFFICIENCY si el hardware está crítico.
    """
    telemetry.info(f"🚀 [IGNITE] Iniciando Misión OSAA v5.0: {goal}")

    # --- PERCEPCIÓN: Análisis situacional ---
    try:
        situational_context = perception.analyze_situation(goal)
        detected_mode = situational_context.get("mode", mode)
        telemetry.info(f"🔍 [IGNITE] Percepción: modo detectado = {detected_mode}")
        # Usar el modo detectado si es más restrictivo
        if detected_mode == "EFFICIENCY" and mode != "EFFICIENCY":
            telemetry.info("⚠️ [IGNITE] Percepción recomienda EFFICIENCY. Aplicando.")
            mode = "EFFICIENCY"
    except Exception as e:
        telemetry.warning(f"⚠️ [IGNITE] Percepción falló ({e}). Usando modo: {mode}")

    # --- LANZAMIENTO: Delegar al enjambre distribuido ---
    launcher = SwarmLauncher()
    result = await launcher.launch(goal, mode)

    status = result.get("status", "UNKNOWN")
    mission_id = result.get("mission_id", "N/A")
    iterations = len(result.get("iterations", []))

    telemetry.info(
        f"✨ [IGNITE] Misión {mission_id} finalizada — "
        f"Status: {status}, Iteraciones: {iterations}"
    )

    return result


if __name__ == "__main__":
    order = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Optimización Core"

    # Soporte de modo por argumento: --mode DIALECTIC
    mode = "DIALECTIC"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1].upper()
            # Limpiar del order
            order = order.replace(f"--mode {sys.argv[idx + 1]}", "").strip()

    result = asyncio.run(execute_mission(order, mode))
    print(f"\n📋 Resultado: {result.get('status', 'N/A')}")
