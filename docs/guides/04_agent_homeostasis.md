# 04 Homeostasis del Agente (OSAA v6.0)

**Módulo Core:** `scripts/agent_runner.py`
**Alias Arquitectónico:** "El Ciclo Vital" / `AgentRunner.run()`

## 1. Topología del Motor Lógico Central

En arquitecturas tradicionales, el agente es una función infinita (`while True`) de peticiones y respuestas con el LLM. En OSAA v6.0, el `AgentRunner` es un daemon diseñado para mantenerse **vivo, cuerdo y dentro del presupuesto**. El objetivo principal de su diseño es preservar la homeostasis térmica del sistema (financiera y de VRAM).

### Ciclo Vital Homeostático
Cada ronda en el `Event Loop` del Agente atraviesa filtros biológicos innegociables:

1. **Espera Relacional (`DialecticTurnManager`):** Ningún agente habla por hablar. A través de bloqueos atómicos IPC, el agente verifica si es su turno. Si se estanca (Timeout), el agente prefiere abortar la misión (`TURN_TIMEOUT`) a enloquecer gastando VRAM en alucinaciones o compitiendo destructivamente.
2. **Chequeo Metabólico (`TokenTracker` & `MCU`):** Antes de componer el Prompt, se interpela la "Unidad Médica" (MCU). Si el agente ha roto el presupuesto configurado en Dólares u operaciones, se declara estado `STARVING` y frena en seco con un `METABOLIC_EXHAUSTION`.
3. **Poda Sináptica (`LogShredder`):** Si el tracking del contexto (historial del prompt) infiere que la ventana se acerca al límite (ej. Llama-3 de 70B), el agente fuerza una *autodescripción* (destilación) de su identidad para purgar su contexto de tokens innecesarios, manteniéndose lúcido.
4. **Cognitive Pre-Flight:** Fase ineludible descrita en la *Guía 01_cognitive_cortex*.
5. **Inferencia LLM:** El puente (`LLMBridge`) ensambla finalmente los contextos reducidos, procesados y pre-pensados. 

## 2. Invariantes del Sistema para Agentes

Si estás diseñando un nuevo Runner o ampliando sus capacidades operativas:

- **No asumas estado global RAM compartido:** El `AgentRunner` se lanza como un sub-proceso puro e independiente. Nunca debe intentar compartir variables en memoria RAM con otro Agente. Todo debe transitar por la Capa de Eventos (`event_bus.py`).
- **Tolerancia Corta a la Frustración:** Las muertes algorítmicas (Rate Limits 429 persistentes) están diseñadas para detenerse de inmediato y activar el reflejo sensorial hacia el `NeuroVision`. Si detectas "Asfixia Metabólica", **no la atrapes** con bloques silenciosos `except`. Déjala fluir hacia la red telemétrica. El fracaso ruidoso evita costos financieros masivos.
- **Roles como Lentes Cognitivos:** La asignación de roles ('proponent', 'adversary', 'optimizer') no es solo un prompt. Cambia fundamentalmente qué herramientas inyecta la orquestación (ej. a un 'adversary' se le exige dudar, invocando herramientas de inyección de duda del bus). No cruces las herramientas.
