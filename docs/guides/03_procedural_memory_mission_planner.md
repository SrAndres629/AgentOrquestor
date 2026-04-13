# 03 Memoria Procedimental y El Orquestador (OSAA v6.0)

**Módulo Core:** `core/mission_planner.py`
**Alias Arquitectónico:** "El Hipocampo de Misiones" / `superpowers`

## 1. Topología del Enrutamiento Dinámico (Mission DAG)

El objetivo base del `MissionPlanner` no es solo "dividir objetivos grandes en chicos" a través del `LLMBridge`. Su propósito arquitectónico real es inyectar metodologías que garanticen la compleción de objetivos complejos sin descansar ciegamente en las habilidades del `AgentRunner`. El planificador altera el grafo (DAG) para obligar comportamientos específicos.

### La Falacia del "Prompt de Metodología"
En sistemas previos, si querías que el Agente programara usando Test-Driven Development (TDD), se le añadía la palabra mágica "TDD" en el prompt. El LLM ignoraba esta indicación debido al ruido atencional en contextos largos o asfixia metabólica. 

**En OSAA v6.0, no se sugiere una metodología, se fuerza estructuralmente (Procedural Memory).**

## 2. Inyección de Instintos: Superpowers
Durante la planificación, el `MissionPlanner.audit_capabilities()` revisita y evalúa qué herramientas o rutinas están habilitadas en el clúster. Si la meta entraña complejidad operativa (palabras clave del usuario como 'arquitectura', 'refactorizar', 'core', 'optimización'), automáticamente categoriza la tarea como `SLOW`.

Al ocurrir esto, el planificador no solo usa `brainstorming` del `mcp_superpowers`. 
También inyecta "nodos obligatorios" en la Misión, dictando sub-trazos estructurales al Runner. Al construir el DAG final de la misión, se encarga de que todo actor tenga las restricciones y herramientas requeridas de `superpowers` como requisitos previos.

### Invariant para Desarrolladores de IA
Si estás planeando la ejecución o ajustando el MissionPlanner:
1. **Auditoría Estricta:** Las heurísticas de "capacidades faltantes" dictan un bootstrap loop (`M_0_BOOTSTRAP`) antes del arranque. Si faltan `superpowers` y el plan es lento, no iniciar el enjambre; obligar descargas/registros.
2. **Nodos Aislados:** Si el planificador exige el uso de un sub-agente (e.g. `subagent_driven_development`), la topología demanda que el nodo aisলে del GraphRAG dependencias colaterales. Ningún agente Runner actuando como Developer debería mezclar tareas analíticas con testeo unitario, debe haber un salto procedural explícito (hilo `Reviewer` -> hilo `Testing`).
