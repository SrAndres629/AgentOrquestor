# [OSAA v5.0] CORE METAPROMPT: EL CÓDICE DE LA CREACIÓN (THE META-GUIDE)

<meta_context>
Este documento es la Guía Cero. Establece el estándar de ingeniería de prompts (XML/Markdown) que DEBE usarse para redactar cualquier nueva guía, protocolo o modelo mental dentro del ecosistema AgentOrquestor. Su objetivo es garantizar que el LLM (Antigravity/Gemini) procese las reglas con máxima fidelidad sin alucinar.
</meta_context>

<mental_model>
**La Matriz de Forja (The Forge Matrix)**
Imagina que las guías no son texto, son cartuchos de software que se insertan en el cerebro de un agente. Si el cartucho tiene una forma diferente, la consola (el LLM) no lo leerá correctamente, el agente se confundirá y consumirá tokens de más. Toda nueva guía debe tener los mismos "pines de conexión" (Etiquetas XML) para encajar perfectamente en la arquitectura.
</mental_model>

<core_directives>
1. **Obligatoriedad de Etiquetas XML:** Toda guía maestra debe estructurarse utilizando las 5 etiquetas fundamentales: `<meta_context>`, `<mental_model>`, `<core_directives>`, `<state_machine>` y `<output_contract>`.
2. **Uso de Modelos Mentales Analógicos:** La etiqueta `<mental_model>` es la más crítica. Los LLMs asimilan reglas abstractas mucho mejor si se les da una analogía física (ej. "Eres un Juez ciego", "Eres un Buzo con oxígeno limitado"). Nunca crees una guía sin una metáfora fuerte.
3. **Imperativo, no Sugerente:** Las directivas deben redactarse como leyes absolutas. Usa verbos como "DEBES", "ESTÁ ESTRICTAMENTE PROHIBIDO", "NUNCA". Evita palabras débiles como "deberías intentar" o "es recomendable".
4. **Acotación de Salida (Output Contract):** Si la guía define a un agente que produce archivos o código, el `<output_contract>` debe contener un bloque de código EXACTO mostrando cómo se ve el resultado esperado.
</core_directives>

<state_machine>
Para crear una nueva guía, el creador (humano o IA) debe seguir este flujo:
* **[STATE: IDENTIFY]**: Definir qué vacío cognitivo o de seguridad tiene el enjambre.
* **[STATE: METAPHORIZE]**: Crear la analogía central (El Modelo Mental).
* **[STATE: DRAFT]**: Escribir las 3-4 reglas absolutas en `<core_directives>`.
* **[STATE: INJECT]**: Guardar el archivo como `docs/guides/XX_nombre.md` para que el script de percepción lo asimile en el próximo reinicio.
* **[STATE: WIRE]**: (Manual/Hardware) Asegurar que el código Python referencie la guía en el system_prompt del agente correspondiente.
</state_machine>

<output_contract>
(El contrato de salida de esta guía es el propio formato en el que está escrita. Toda nueva guía debe ser un clon estructural de este mismo documento).
</output_contract>

## Índice de Protocolos OSAA v6.0

01. **Worker Protocol:** Conducta y ejecución de agentes.
02. **Dialectic Engine:** Consenso y enrutamiento (Consensus Score).
03. **Bootstrap Protocol:** Autofabricación de herramientas (SeedOrchestrator).
04. **Tool Blueprint:** Diseño de nuevos MCP Servers.
05. **Chronicler Protocol:** Gestión de memoria a largo plazo.
06. **Mission Planner:** Descomposición de objetivos complejos.
07. **Self-Awareness:** Monitoreo de introspección cognitiva.
08. **Sepulturero Protocol:** Limpieza de procesos y hardware.
09. **Inquisidor Protocol:** Verificación de integridad y seguridad.
10. **Metabolic Governor:** Control de consumo de tokens y VRAM.
11. **TDD Loop:** Ciclo de desarrollo guiado por pruebas.
12. **Hardware Grounding:** Conexión con sensores físicos del host.
13. **Business Standard:** Alineación con objetivos de negocio.
14. **MCP Proxy Protocol:** Interfaz de herramientas externas.
15. **Disaster Recovery:** Botón de pánico y restauración de bus.
16. **Telemetry Optics:** Visualización de trazas neuronales.
17. **MCP Unified Protocol:** Cableado real entre main.py y Core.
18. **Swarm Deployment:** Orquestación en tmux y aislamiento.
19. **Ouroboros Weaver:** Bucle autónomo de autocuración.
20. **Context Shredder:** Optimización de VRAM y destilación de logs.
