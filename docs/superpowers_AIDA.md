# SPECIFICATION AIDA: Procedural Cortex (Superpowers)

**Target System:** AgentOrquestor v6.0
**Module Component:** `core/mission_planner.py` -> `<core_directives>`
**Integration Nature:** Inyección de Metaprompt Sistemático (Nervioso-Procedimental)

## 1. Análisis Arquitectónico
Superpowers no es una herramienta cognitiva Pura (como sequential-thinking) ni Sensorial (como NeuroVision), es una **Metodología Estricta**. Se integró inyectando su "instinto de flujo de trabajo" directamente en el cerebro del General de Guerra (`MissionPlanner`). El planificador ahora generará misiones que respetan la cadencia: Planificación -> TDD -> Desarrollo de Subagentes -> Revisión.

## 2. Invariantes del Sistema (Leyes)
- **Constraint 1:** Superpowers DEBE usarse para modificar archivos del proyecto. `AgentOrquestor` no debe editar en ráfaga (zero-shot) sin validaciones `subagent-driven`.
- **Constraint 2:** Si el usuario pide un refactor complejo, se debe generar un DAG asincrónico para evitar sobrecargar la memoria de un solo agente.

## 3. Modelo Mental de Fallo (Risks & Bottlenecks)
- **Riesgo:** El AgentOrquestor colapsa si el repositorio no usa *Git Worktrees*, lo que es fundamental para el `using-git-worktrees` de superpowers. 
- **Defensa en Profundidad:** El LLMBridge truncará (GUIDE 04) comandos que arrojen excesivos diffs de git, evitando la "asfixia" del agente (Token Overflow).

## 4. Estado de Validación
- Mapeo Categorial: Agregado a la heurística de capacidades `planner.audit_capabilities()` para prever la necesidad de sub-agentes de Testing o Planificación. 

*Estado: 100% OPERATIVO. VALIDADO VÍA METAPROMPT INJECTION.*
