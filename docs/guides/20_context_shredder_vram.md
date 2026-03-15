# [OSAA v6.0] CORE METAPROMPT: GESTIÓN DE CONTEXTO Y SHREDDER (THE TOKEN OPTIMIZER)

<meta_context>
Este documento rige la optimización de VRAM y tokens mediante el Shredder. Define las reglas para recortar contextos masivos sin perder la esencia semántica, permitiendo que agentes complejos funcionen en hardware limitado (RTX 3060/4060).
</meta_context>

<mental_model>
**El Bibliotecario Triturador (The Shredding Librarian)**
Imagina un bibliotecario que debe meter un libro de 1000 páginas en un sobre pequeño. En lugar de romper las páginas al azar, identifica los capítulos clave, las conclusiones y las advertencias, y tira el resto. El agente recibe un resumen denso y vital, no un montón de papel picado. Es la diferencia entre truncar datos y destilar conocimiento.
</mental_model>

<core_directives>
1. **Preservación de Heurísticas:** El Shredder DEBE priorizar líneas que contengan palabras clave (ERROR, CRITICAL, SUCCESS, TODO, FIXME) al recortar logs o código.
2. **Límite de Hardware Estricto:** Si el HardwareMonitor detecta >85% de uso de VRAM, el Shredder debe aplicar un modo de "Recorte Agresivo" (reducción del context_window en un 50%).
3. **Cero Alucinaciones por Recorte:** El agente debe ser notificado mediante un tag XML si su contexto ha sido recortado, para que sepa que hay información omitida.
</core_directives>

<state_machine>
Proceso de Destilación:
1. Ingesta de Datos Raw.
2. Análisis de Palabras Clave de Prioridad.
3. Truncado por Límite de Caracteres (MAX_CONTEXT_CHARS).
4. Inyección de Marcadores de Omisión [...].
5. Entrega de Contexto Optimizado.
</state_machine>

<output_contract>
Contexto Destilado:
```markdown
## <context_shredded_notice>
Este log ha sido destilado por Shredder v4.0. Se han omitido 450 líneas irrelevantes.
</context_shredded_notice>

[...]
2024-03-14 12:00:01 ERROR: Failed to allocate VRAM
[...]
2024-03-14 12:05:00 SUCCESS: Mission Goal Reached
```
</output_contract>
