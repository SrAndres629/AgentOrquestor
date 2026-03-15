# [OSAA v6.0] CORE METAPROMPT: DESPLIEGUE DE ENJAMBRE Y TMUX (THE SWARM ORCHESTRATOR)

<meta_context>
Este documento rige la orquestación de procesos aislados mediante SwarmLauncher. Define cómo se fragmenta la cognición en sesiones de tmux para garantizar que cada agente tenga su propio espacio de memoria y CPU, comunicándose únicamente a través del Bus IPC (.cortex/bus_buffer.jsonl).
</meta_context>

<mental_model>
**La Colmena de Celdas Aisladas (The Isolated Cell Hive)**
Imagina una colmena donde cada celda es una terminal de tmux. Las abejas (agentes) no pueden volar de una celda a otra; solo pueden dejar mensajes en un pequeño buzón compartido (el Bus de Eventos). Si una abeja muere (crashea), su celda se limpia sin afectar al resto de la colmena. El SwarmLauncher es la Abeja Reina que vigila todas las celdas desde el exterior.
</mental_model>

<core_directives>
1. **Aislamiento por Sesión:** Cada agente DEBE ejecutarse en una sesión de tmux nombrada única con el prefijo 'osaa_{mission_id}_{agent_name}'.
2. **Invariabilidad de ID:** El mission_id debe ser generado UNA VEZ al inicio y propagado a todas las terminales. Está prohibido regenerar la ID durante la misión.
3. **Protocolo del Sepulturero:** Al finalizar la misión o detectar un aborto, el sistema DEBE ejecutar mux.kill_all() para limpiar el hardware y evitar procesos zombis.
</core_directives>

<state_machine>
Ciclo de Vida del Swarm:
1. Build Topology (Registry.yaml).
2. Create Mission Directory (.cortex/missions/{id}).
3. Forge Brains (Context injection).
4. Spawn tmux sessions (AgentRunner).
5. Poll for Consensus/Handoff (Watchdog).
6. Cleanup (Kill sessions).
</state_machine>

<output_contract>
Estructura de la Misión:
```text
.cortex/missions/{id}/
├── manifest.json
├── brains/contexto_{agent}.md
├── reports/{agent}_report.md
└── logs/{session}.log
```
</output_contract>
