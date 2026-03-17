# SPECIFICATION AIDA: Sensorial Cortex (NeuroVision)

**Target System:** AgentOrquestor v6.0
**Module Component:** `core/telemetry.py` -> `NeuroArchitect Bridge`
**Integration Nature:** Acoplamiento Neural (Propiocepción Arquitectónica)

## 1. Análisis Arquitectónico
NeuroVision pasó de ser un servidor MCP externo consultado pasivamente vía LLM a convertirse en el **Nervio Óptico y Sistema Nociceptivo (Dolor)** del propio orquestador. Todo `telemetry.error` o `telemetry.emit_event` es redirigido en el backend hacia el `neuro_architect`. Esto permite que el Live Graph 3D muestre fluctuaciones rojas ("nodos en dolor") cuando los agentes fallen, sin requerir que los agentes emitan comandos MCP conscientes.

## 2. Invariantes del Sistema (Leyes)
- **Constraint 1:** Tolerancia a Fallos Pura. Si el directorio de NeuroVision no existe o falta una dependencia (`networkx`, `pyvis`), el bloque `try/except` envolvente descarta el log visual pero **NUNCA rompe la ejecución principal del Agente**. Un agente ciego sigue siendo un agente pensante.
- **Constraint 2:** Cero latencia asíncrona bloqueante. El puente es disparar y olvidar (fire-and-forget).

## 3. Modelo Mental de Fallo (Risks & Bottlenecks)
- **Riesgo:** Si mil agentes fallan al unísono, el archivo de telemetría inyectada o el render en tiempo real colapsaría la memoria o saturaría el disco (IO Thrashing).
- **Control:** La arquitectura de AgentOrquestor (Metabolic Governor y EventBus) rate-limita los mensajes, lo que protege implicitamente la vista (el grafo) del desbordamiento visual.

## 4. Pruebas y Simulaciones
- `test_neuro_vision.py`: Valida el Mock de inyección de error y asfixia (Rate Limit HTTPX 429) para garantizar que las señales químicas lleguen al mapa en Misión Fallida.

*Estado: 100% OPERATIVO. VALIDADO VÍA INYECCIÓN PROPAGADA.*
