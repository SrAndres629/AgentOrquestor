# SKILL: OUROBOROS WEAVER (GENERADOR DE BUCLES)

**Gatillo de Activación:** Se activa cuando el humano usa frases como "hasta que funcione", "repara todos los errores", "asegúrate de que cumpla lo que dice" o "bucle de resolución".

**Directiva Core:**
1. **Definición de Salida (Exit Condition):** Nunca inicies un bucle sin definir cómo se rompe. ¿Es un test unitario que debe dar verde? ¿Es un endpoint que debe devolver HTTP 200?
2. **Forja del Arnés (The Harness):** No intentes mantener el bucle en tu propia ventana de contexto (gastarás todos los tokens). En su lugar, ESCRIBE un script de Python en la carpeta `scripts/temp_loop_<id>.py`.
3. **Anatomía del Script de Bucle:** El script que generes DEBE tener esta estructura:
   - `while iterations < MAX_LIMIT:` 
   - Ejecuta la prueba física (ej. correr pytest o hacer un request).
   - `if success: break`
   - `else:` Captura el `traceback` del error y llama a la herramienta MCP `launch_swarm` o `inject_orchestration_command` inyectando el error exacto para que el enjambre lo resuelva.
   - Espera a que el enjambre termine (monitoreando `.cortex/bus_buffer.jsonl` o `consensus.lock`). 
4. **Ejecución y Desapego:** Una vez que escribas el script de bucle, ejecútalo en un subproceso (`subprocess.Popen`) e informa al humano: "Bucle autónomo iniciado. Te avisaré cuando la condición de éxito sea absoluta."
