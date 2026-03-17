# 00 Meta Arquitectura: Plano de Sistemas OSAA v6.0 (AgentOrquestor)

**PÚBLICO OBJETIVO:** Agentes de IA, Arquitectos de Sistemas y Meta-Orquestadores que requieran modificar o interactuar profundamente con la estructura base de AgentOrquestor.

## 1. Visión Fundamental y Filosofía de Diseño
AgentOrquestor ya no es un "script de invocación de herramientas LLM". El paradigma **OSAA v6.0** (Open Swarm Autonomous Architecture) transforma el código en una emulación **fisiológica biológica**.

**NO** debes pensar en los módulos como clases o funciones aisladas. **DEBES** pensar en ellos como órganos de un sistema biológico interdependiente:
- Si cortas un flujo de datos sin mantener el homeostasis, el sistema sufre asfixia.
- El "dolor" del sistema (errores) no se loggea pasivamente; dispara reflejos hacia herramientas visuales.
- El razonamiento no es una opción de herramienta, es una necesidad *pre-motora* ineludible.

## 2. Mapa Topológico del Sistema (Blueprint)

El flujo vital de una ejecución de Agente atraviesa estrictas y separadas capas de procesamiento. No puedes alterar este flujo sin comprender sus implicancias.

### Capa 1: Sistema Pre-Motor (Cognitive Pre-Flight)
- **Módulo responsable:** `core/cognitive_cortex.py`
- **Función:** Genera la "Intención de Actuar".
- **Arquitectura:** Operando bajo un modelo Zero-Shot aislado (`LLMBridge` sin acceso a herramientas operativas), lee el estado del debate y genera un Árbol de Pensamiento Estructurado (`sequential-thinking`).
- **Restricción Arquitectónica:** Ningún agente (LLM principal) en `agent_runner.py` puede recibir permisos para ejecutar herramientas mutantes sobre el entorno hasta que este córtex haya inyectado la conclusión secuencial inmutable en su `system_prompt`. El motor base lógico *debe* recibir la conclusión estructurada de forma axiomática.

### Capa 2: Médula Espinal y Reflejos (EventBus & Telemetry)
- **Módulos responsables:** `core/event_bus.py`, `core/telemetry.py`
- **Función:** Comunicación sincrónica atómica IPC (Buzones) y reflejos incondicionados.
- **Arquitectura:** El Event Bus no bloquea hilos concurrentes. Escribe eventos inmutables en buzones `.jsonl` protegidos por atomic locks (`fcntl`).
- **Restricción Arquitectónica (Arco Reflejo):** La telemetría inyectada en el bus monitorea eventos de asfixia (e.g., HTTP 429 de Rate Limit) o `FATAL_ERROR`. Al detectarlos, *deben* forzar un disparador asíncrono ciego (`_trigger_pain_reflex`) hacia los MCPs de propiocepción topológica (NeuroVision). No dependas del LLM para notificar el error; es un arco reflejo sistémico de hard-code.

### Capa 3: Sistema Autónomo Procedimental (MissionPlanner)
- **Módulo responsable:** `core/mission_planner.py`
- **Función:** Diseñar el flujo DAG y proveer "instintos pre-entrenados" (`superpowers`).
- **Arquitectura:** Intercepta la solicitud inicial humana. Evalúa mediante heurísticas (auditoría de capacidades) la complejidad de la tarea demandada.
- **Restricción Arquitectónica:** Si la tarea entra en la clasificación "SLOW" (ej. "refactorización profunda", "arquitectura del core"), el Mission Planner _alterará genéticamente_ el DAG inyectando forzosamente metodologías complejas procedimentales de sub-agentes (como TDD loops o validación estricta de código). No se confía en que el `AgentRunner` individual posea el expertise procedimental adecuado en crudo.

### Capa 4: Ejecución Homeostática (AgentRunner)
- **Módulo responsable:** `scripts/agent_runner.py`
- **Función:** Ciclo base del motor lógico LLM. Ejecuta las decisiones cristalizadas en la Capa 1 utilizando las vías de la Capa 2, bajo la estructura de la Capa 3.
- **Arquitectura:** Corre un bucle temporal donde el agente espera su turno (`DialecticTurnManager`), recibe su presupuesto tokenizado (Hardware Grounding/MCU), recibe su axioma secuencial temporal (Cognitive Pre-Flight), interacciona con su `LLMBridge` para empalmar herramientas (y solo herramientas) base, y al finalizar emite la mutación de entorno al buzón.

## 3. Principio de Inyección Transversal para Desarrolladores de IA
Si tú, Agente Desarrollador, necesitas implementar una nueva característica:
1. **¿Cambia CÓMO el agente planea un comportamiento intrincado?** Pertenece inyectado a la Capa 1 Córtex (`cognitive_cortex.py`).
2. **¿Requiere que distintos agentes sepan del nuevo estado?** Escríbelo como buzón Atómico (IPC) de la Capa 2 (`event_bus.py`). No uses memoria RAM nativa.
3. **¿Aplica metodologías nuevas como una habilidad preestablecida para el Agente?** Agrega el patrón a la Capa 3 (`mission_planner.py`).

**Fin del Archivo de Diseño Base.**
