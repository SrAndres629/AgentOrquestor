# SPECIFICATION AIDA: Cognitive Cortex (Sequential Thinking)

**Target System:** AgentOrquestor v6.0
**Module Component:** `core/cognitive_cortex.py`
**Integration Nature:** Primitiva Funcional Nativa (Hardwired)

## 1. Análisis Arquitectónico
El razonamiento reflexivo ("Chain of Thought" ramificado) es una capacidad metabólica *base*, no una herramienta periférica. Al inyectar el código de `sequential-thinking` (originalmente en TypeScript/Node) directamente en el subprocesamiento de Python, eliminamos la latencia IPC de stdio y garantizamos que la "Voz Interna" del enjambre corra dentro de su capa segura.

## 2. Invariantes del Sistema (Leyes)
- **Constraint 1:** El agente *no puede* ser engañado si omite parámetros. Validado por Pydantic Models.
- **Constraint 2:** Cada bucle recursivo (`nextThoughtNeeded=True`) debe contabilizarse en el `Metabolic Governor` para evitar ataques de asfixia (exhaustión de VRAM o tokens puros por *overthinking*).

## 3. Modelo Mental de Fallo (Risks & Bottlenecks)
- **Riesgo:** Un agente en Modo SLOW ("Inquisidor") se queda atrapado en un bucle mental infinito incrementando `totalThoughts` sin cesar.
- **Defensa en Profundidad (Diseñada en Fase 3):**
  - El Event Bus IPC y el Runner cortan tras `MAX_TOOL_ROUNDS`. El pensamiento secuencial respeta la asfixia del Runner.

## 4. Estructura de Integración API
Se mapeó exitosamente:
```python
tool_def = {
    "name": "sequentialthinking",
    # Mapea 1:1 con la especificación original, pero ruteado vía RAM (mcp_proxy bypass)
}
```

*Estado: 100% OPERATIVO. VALIDADO VÍA HARDWIRING.*
