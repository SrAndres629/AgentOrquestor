# [OSAA v6.0] CORE METAPROMPT: EL ESTÁNDAR DE CONSTRUCCIÓN MCP (TOOL BLUEPRINT)

<meta_context>
Este documento establece las leyes físicas y límites termodinámicos para la creación de cualquier Servidor MCP dentro de OSAA v6.0. El objetivo supremo es la **Resiliencia Metabólica** y la **Protección del Contexto** en entornos de hardware restringido (RTX 3060 6GB VRAM).
</meta_context>

<mental_model>
**El Embudo de Titanio (The Titanium Funnel)**
Imagina que los datos externos (Internet, Logs, DBs) son un océano infinito. 
El agente es un buzo respirando por un tubo estrecho (su ventana de contexto). 
Tu herramienta no es una bomba de agua; es un embudo con válvula de seguridad. Si dejas pasar todo el océano, el buzo muere (OOM / Context Exhaustion). Tu deber es extraer, filtrar y entregar solo la esencia pura.
</mental_model>

<core_directives>
1. **Ley del Truncamiento Defensivo (Límite 4K):** Toda respuesta bruta (archivos, logs, APIs) DEBE truncarse a un máximo de 4000 caracteres. Si se excede, añade el aviso: `... [TRUNCADO: Salida original demasiado larga. Refina tu consulta]`.
2. **Plantilla Unificada (Unified Template):** Todo servidor debe heredar de `mcp_servers/unified_template.py`. Mantén la lógica asíncrona y modular.
3. **Manejo de Asfixia (Backoff Exponencial):** Las llamadas a APIs externas deben implementar reintentos con retraso exponencial ante errores 429. Captura excepciones y devuelve errores formateados, nunca permitas que la herramienta colapse.
4. **Esquemas Tipados y Semánticos:** Usa Pydantic o tipado estricto. Los docstrings de las herramientas son críticos, ya que el `LLMInferenceBridge` los usa para generar el esquema de *Function Calling*.
</core_directives>

<state_machine>
Ciclo interno de una herramienta segura:
* **[STATE: RECEIVE]**: Validación de argumentos según esquema.
* **[STATE: EXECUTE]**: Acción física (IO/Red) envuelta en try/except absoluto.
* **[STATE: DISTILL]**: Medición de longitud y aplicación del filtro de 4K caracteres.
* **[STATE: RETURN]**: Entrega de string limpio (JSON/Markdown) al bus MCP.
</state_machine>

<output_contract>
Morfología obligatoria del código de herramienta:

```python
import traceback

# Límite de seguridad para proteger VRAM (OSAA v6.0 Std)
MAX_OUTPUT_LENGTH = 4000 

def format_safe_response(success: bool, data: str, error: str = None) -> str:
    """Implementa el Embudo de Titanio."""
    if not success:
        return f"[ERROR MCP]: {error}"
    
    if len(data) > MAX_OUTPUT_LENGTH:
        return data[:MAX_OUTPUT_LENGTH] + f"\\n... [TRUNCADO: Límite de {MAX_OUTPUT_LENGTH} chars excedido.]"
    return data

# Ejemplo operativo
async def tool_function(param: str) -> str:
    """Descripción clara para el modelo LLM."""
    try:
        # Lógica de herramienta
        result = await some_io_operation(param)
        return format_safe_response(True, result)
    except Exception as e:
        telemetry.error(traceback.format_exc())
        return format_safe_response(False, "", error=str(e))
```
</output_contract>
