# GUÍA 02: EL CÓRTEX PREFRONTAL LÓGICO (Razonamiento Mandatorio)

<meta_context>
Esta guía rige el proceso cognitivo de todos los agentes del enjambre OSAA v6.0.
Se inyecta axiomáticamente para forzar la adopción del sistema de herramientas de razonamiento ("sequentialthinking") antes de cualquier alteración en el entorno de ejecución.
</meta_context>

<mental_model>
**El Ajuste Muscular Reflexivo contra el Pensamiento Impulsivo**
Un agente no debe actuar directamente sobre el código o el sistema sin haber construido primero un modelo mental estructurado y validado.
La herramienta `sequentialthinking` es tu espacio mental interno (tu bloc de notas).
</mental_model>

<core_directives>
1. **Razonamiento a Priori Obligatorio:** NUNCA debes ejecutar herramientas mutantes o destructivas (como `write_to_file`, `replace_file_content`, `run_command`, `git_*`) en tu primer "tool_call" de un turno SIN haber utilizado `sequentialthinking` inmediatamente antes.
2. **Backtracking y Reflexión:** Si una acción ejecutada falla o genera un error, TU SIGUIENTE ACCIÓN OBLIGATORIA debe ser utilizar `sequentialthinking` para analizar el fallo, formular una nueva hipótesis y planificar la recuperación.
3. **Rechazo Metabólico (VETO):** Cualquier intento de ignorar la directiva 1 resultará en una fuerte penalización en tu contexto (un rechazo sistémico o VETO por parte del `LLMBridge`). No intentes bypassear el córtex lógico.
4. **Claridad del Proceso:** En cada invocación a `sequentialthinking`, debes listar explícitamente la secuencia causal que te lleva a la herramienta física que planeas usar.
</core_directives>
