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
from core.mission_planner import planner
from core.chronicler import chronicler


async def execute_mission(goal: str, mode: str = "DIALECTIC"):
    """
    Punto de entrada evolutivo del enjambre distribuido.
    """
    telemetry.info(f"🚀 [IGNITE] Iniciando Misión OSAA v5.0: {goal}")

    # --- AUDITORÍA DE CAPACIDADES (Evolución Autónoma) ---
    audit = planner.audit_capabilities(goal)
    if audit.get("bootstrap_needed"):
        telemetry.warning("🏗️ [IGNITE] Iniciando Misión Cero (Autofabricación)...")
        bootstrap_goal = planner.create_bootstrap_mission(goal, audit["missing_capabilities"])
        launcher = SwarmLauncher()
        await launcher.launch(bootstrap_goal, mode="EFFICIENCY") # Bootstrap suele ser ligero
        telemetry.info("✅ [IGNITE] Misión Cero completada. Procediendo a Misión Principal con arsenal actualizado.")

    # --- PERCEPCIÓN: Análisis situacional ---
    try:
        situational_context = perception.analyze_situation(goal)
        detected_mode = situational_context.get("mode", mode)
        # ... logic remains same ...
        if detected_mode == "EFFICIENCY" and mode != "EFFICIENCY":
            mode = "EFFICIENCY"
    except Exception as e:
        telemetry.warning(f"⚠️ [IGNITE] Percepción falló ({e}). Usando modo: {mode}")

    # --- LANZAMIENTO: Delegar al enjambre distribuido ---
    launcher = SwarmLauncher()
    result = await launcher.launch(goal, mode)

    status = result.get("status", "UNKNOWN")
    mission_id = result.get("mission_id", "N/A")
    
    # --- MEMORIA: Persistencia evolutiva ---
    chronicler.remember_mission(mission_id, status, f"Misión: {goal}")

    telemetry.info(
        f"✨ [IGNITE] Misión {mission_id} finalizada — "
        f"Status: {status}"
    )

    return result


if __name__ == "__main__":
    # Soporte de modo por argumento: --mode DIALECTIC --goal "Objetivo"
    mode = "DIALECTIC"
    order = ""
    
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1].upper()
            
    if "--goal" in sys.argv:
        idx = sys.argv.index("--goal")
        if idx + 1 < len(sys.argv):
            order = sys.argv[idx + 1]
    else:
        # Fallback: todos los args que no sean --mode
        remaining = []
        skip_next = False
        for i, arg in enumerate(sys.argv[1:], 1):
            if skip_next:
                skip_next = False
                continue
            if arg == "--mode":
                skip_next = True
                continue
            remaining.append(arg)
        order = " ".join(remaining) if remaining else "Optimización Core"

    result = asyncio.run(execute_mission(order, mode))
    print(f"\n📋 Resultado: {result.get('status', 'N/A')}")
