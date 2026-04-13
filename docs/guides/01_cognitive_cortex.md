# 01 El Córtex Cognitivo Pre-Motor (OSAA v6.0)

**Módulo Core:** `core/cognitive_cortex.py`
**Alias Arquitectónico:** "Cognitive Pre-Flight" / `generate_zero_shot_thought`

## 1. Topología del Razonamiento Secuencial

En arquitecturas LLM antiguas, el razonamiento estructurado (como `sequential-thinking`) era una herramienta expuesta al agente. El agente *decidía* si la llamaba o si directamente actuaba (ej. ejecutaba test, corría shell, etc.). Esto causaba impulsividad destructiva.

**En AgentOrquestor (OSAA v6.0), el razonamiento es una capa pre-motora ineludible.**
No puedes alterar este comportamiento sin comprometer la estabilidad cognitiva del enjambre. 

### Diagrama de Flujo del Lóbulo Lógico:
1. El `AgentRunner` recibe su turno en el ciclo. Evalúa el estado del debate (`debate_history`) y su tarea actual (`current_task`).
2. *Antes* de instanciar al `LLMBridge` principal con permisos de herramientas, el Runner invoca asíncronamente `cognitive_cortex.generate_zero_shot_thought(role, history, task)`.
3. El `CognitiveCortex` inicializa una inferencia **aislada y sin herramientas** (Zero-Shot) con el LLM, exigiendo una disección Chain of Thought táctica de la situación.
4. El LLM devuelve un Árbol Sequencial de Pensamiento cristalizado.
5. El `AgentRunner` **muta el contexto** de la inferencia primaria asumiendo esta cadena de pensamientos como un axioma pre-calculado: _"He pensado en esto y mi plan inmutable es X. Ahora usaré las herramientas."_

## 2. Invariantes del Sistema para Agentes

Si estás diseñando o refactorizando lógica en el orquestador:

- **No expongas `sequentialthinking` como herramienta general de nuevo.** El agente principal *no debe poder decidir* pensar a medias. Su única función en este bucle es ejecutar mecánicamente el axioma dictado por el `Cognitive Pre-Flight`.
- **Bypass Heurístico:** La única forma arquitectónicamente correcta de bypassear el córtex es si la tarea exige latencias sub-100ms (respuestas puramente reflejas). Si diseñas algo así, debe estar en un subsistema paralelo, nunca en el bucle principal de `agent_runner.py`.
- **Estructura Esperada del Output del Córtex:** El resultado del córtex debe ser siempre analítico, enumerando riesgos y pasos. No debe contener comandos listos a la ejecución directa, solo la lógica a procesar por el agente que _sí_ tiene las herramientas.

## 3. Interfaces Base

```python
async def generate_zero_shot_thought(self, agent_role: str, context: str, current_task: str) -> str:
    """
    Motor inyectado en la fase 1 del bucle AgentRunner.
    Provee la cadena inmutable para aislar el razonamiento de la acción reactiva.
    """
```
