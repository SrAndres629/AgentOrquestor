# [OSAA v6.0] GUÍA 21: ALTAS CAPACIDADES Y NÚCLEOS COGNITIVOS MCP

**Estado:** ACTIVO
**Nivel de Autorización:** Arquitecto / MissionPlanner

## 1. Naturaleza de las Altas Capacidades
Históricamente, los MCPs se trataban como simples "herramientas externas" (ej. leer un archivo, buscar en la web). En OSAA v6.0, bajo el paradigma SOTA 2026, plataformas de alto nivel como `sequential-thinking`, `superpowers` y `NeuroVision` **NO son herramientas ad-hoc**. Son tejidos fisiológicos integrados directamente en el núcleo del enjambre.

## 2. El Córtex Razonador (Sequential Thinking)
- **Topología:** Hardwired en Python puro (`core/cognitive_cortex.py`). 
- **Propósito:** Previene las alucinaciones "zero-shot" de respuestas inmediatas. 
- **Regla de Oro:** Siempre que un agente enfrente una tarea arquitectónica, de refactorización o de abstracción compleja, DEBE emplear `sequentialthinking` para ramificar sus hipótesis antes de emitir la acción final.

## 3. El Córtex Procedimental (Superpowers)
- **Topología:** Inyectado a nivel Metaprompt en el Generador de DAGs (`core/mission_planner.py`).
- **Propósito:** Transforma el impulso bruto del usuario en un flujo disciplinado.
- **Regla de Oro:** Todo código nuevo o modificado debe someterse al instinto base: `brainstorming` -> `writing-plans` -> `test-driven-development` -> `subagent-driven-development` -> `requesting-code-review`. El Planificador debe fragmentar las misiones obligando a este paso a paso.

## 4. El Córtex Sensorial y Nociceptivo (NeuroVision)
- **Topología:** Acoplado dinámicamente al bus de telemetría global (`core/telemetry.py`).
- **Propósito:** Consciencia propioceptiva de la base de código. 
- **Regla de Oro:** Los agentes no necesitan "decidir" invocar NeuroVision para ser auditados. Cada error de sintaxis, cada falla HTTP 429 (asfixia metabólica) y cada misión completada dispara automáticamente una señal de render 3D (`neuro.ingest_telemetry`), permitiendo al operador (o al agente Warden) observar "sangrar" o "sanar" el grafo arquitectónico en tiempo real. 

## 5. Directiva Crítica de Modificación
Cualquier sub-agente intentando hacer un bypass a este tejido neuronal compuesto será interrumpido por el `ConsensusWatchdog`. El AgentOrquestor es un organismo, no un script plano.
