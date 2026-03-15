# [OSAA v6.0] CORE METAPROMPT: EL PROTOCOLO UNIFICADO MCP (THE TOOL WIRE)

<meta_context>
Este documento define la arquitectura de comunicación entre el Servidor MCP (main.py) y el Núcleo de AgentOrquestor. Es la ley de cableado que elimina los stubs y garantiza que cada llamada a una herramienta (ignite, launch, audit) active lógica física real y no respuestas pre-programadas.
</meta_context>

<mental_model>
**El Sistema Nervioso Periférico (The Peripheral Nervous System)**
Imagina que el Servidor MCP son los dedos y la piel del organismo, y el Core (ignite.py, swarm_launcher.py) es el cerebro. Si los dedos tocan fuego (un error), el sistema debe enviar una señal eléctrica real al cerebro para que retire la mano. Un "Handshake" falso es como un miembro fantasma: el sistema cree que está actuando, pero no hay respuesta física. Cada sinapsis (Tool Call) debe ser una conexión de cobre puro, sin simulaciones.
</mental_model>

<core_directives>
1. **Prohibición de Stubs:** Ninguna herramienta MCP puede devolver un mensaje estático de "OK" o "Iniciando". Debe retornar el resultado real de la ejecución o el error de Python capturado.
2. **Inyección de Dependencias:** El servidor MCP debe usar el entorno virtual (.venv) del proyecto para evitar NameErrors por librerías faltantes como psutil o mcp.
3. **Manejo de Errores Críticos:** Toda falla en el Core debe ser capturada con traceback completo y devuelta al cliente MCP como un error estructurado, permitiendo que el Ouroboros Weaver inicie el bucle de curación.
</core_directives>

<state_machine>
Flujo de una Tool Call:
1. Recepción de Argumentos (JSON Schema).
2. Importación Dinámica del Módulo Core correspondiente.
3. Ejecución Asíncrona (await core_function).
4. Serialización JSON del resultado real.
5. Respuesta al Cliente.
</state_machine>

<output_contract>
Respuesta de éxito (Ejemplo ignite_mission):
```json
{
  "status": "COMPLETED",
  "mission_id": "m_abc123",
  "final_consensus": "Objetivo cumplido. Código desplegado."
}
```
</output_contract>
