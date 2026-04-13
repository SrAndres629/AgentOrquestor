# 02 Sistema Nervioso Central y Arco Reflejo (OSAA v6.0)

**Módulos Core:** `core/event_bus.py`, `core/telemetry.py`
**Alias Arquitectónico:** "El Tronco Encefálico" / `_trigger_pain_reflex`

## 1. Topología del Event Bus (IPC Mailboxes)

En AgentOrquestor v6.0, el `EventBus` es el **único** método arquitectónicamente avalado para la sincronización entre agentes en el Swarm. A diferencia de implementaciones ingenuas en memoria RAM, el bus de OSAA es persistente y tolerante a fallos.

### Reglas de Diseño del EventBus:
- **Comunicación IPC Atómica:** Cada envío de mensaje (Thought, Request, Emit) usa `fcntl` para garantizar bloqueos atómicos sobre archivos `.jsonl`.
- **Aislamiento por Buzón (`read_mailbox`):** El sistema fue rediseñado desde un streaming síncrono frágil hacia un paradigma de buzones asíncronos distribuidos. Cada Agente escribe pasivamente sin bloquear a otros y el "Watchdog" u otros agentes leen cuando les es fisiológicamente posible.
- **Botón de Pánico (`_handle_corrupted_bus`):** Si un agente detecta corrupción en un buzón de `.jsonl` al leerlo, no se crashea. Archiva el buzón corrupto (metodología *Disaster Recovery*) y reinicia el flujo limpio.

## 2. Telemetría y El Arco Reflejo del Dolor (NeuroVision)

La integración profunda de NeuroVision transforma el `EventBus` de un simple pasacables a un Tronco Encefálico activo. La filosofía **no** es que el agente decida alertar al operador. La filosofía es que la alteración homeostática (el error) dispare un evento involuntario.

### Mecánica del Arco Reflejo:
1. Las operaciones críticas en `agent_runner.py` (ej. asfixia por límite de tokens de Groq) o en el `LLMBridge` (sintaxis rota) no retornan simplemente un string rojo.
2. Emiten un evento catalogado como **Dolor** al bus: `FATAL_NETWORK`, `FATAL`, `ERROR`, o `COGNITIVE_DOUBT`.
3. El `EventBus` intercepta internamente el catálogo de dolor en `publish()`. 
4. Inmediatamente y de forma asíncrona (`fire-and-forget` vía `asyncio`), llama a `mcp_proxy.call_tool("report_telemetry")`.
5. **NeuroVision** procesa el pulso de telemetría y colorea o resalta el nodo 3D del Agente particular en los monitores del desarrollador humano.

### Para el Desarrollador del Enjambre:
- **No uses `print()` para debugear flujos complejos de los Agentes.**
- Usa `telemetry.error("Causa de muerte")` o `bus.publish("ERROR", {"razon": "..."})`.
- El sistema se encargará de propagar el impulso de dolor por toda la red sensorial. Si tocas el código de `event_bus.py`, asegúrate de que tus operaciones nunca bloqueen el loop asíncrono primario si el puente de telemetría se cae o expira. Tolerancia fisiológica al fallo: un agente ciego sigue operando.
