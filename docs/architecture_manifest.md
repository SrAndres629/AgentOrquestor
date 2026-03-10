# Manifiesto Arquitectónico: agentOrquestor

**Fase Operativa:** Q1-2026
**Entorno Principal:** Ubuntu Linux Nativo
**Restricciones de Hardware:** 16GB RAM, GPU Nvidia RTX 3060 (6GB VRAM)

Este manifiesto establece las reglas de diseño y arquitectura críticas e inquebrantables para el desarrollo de `agentOrquestor`. La meta del sistema es diseñar un servidor MCP autónomo robusto operando bajo restricciones de grado industrial en inferencia, asegurando determinismo, seguridad de aislamiento y escalabilidad cognitiva.

## 1. Eficiencia Cíclica y Modelos de Inferencia (Optimizando 6GB VRAM)
- **Extracción Lineal (SSM - Mamba):** A fin de prevenir el colapso del límite de VRAM, el backend de LLM primario no utilizará arquitecturas Transformer puras que sufran de complejidad temporal y espacial $O(N^2)$. La inferencia se restringirá a Modelos de Secuencia de Estado (SSM, predeterminando arquitecturas derivativas de *Mamba*) garantizando un escalamiento lineal de contexto sin picos catastróficos de memoria.
- **Decodificación Especulativa (Speculative Decoding):** Para aumentar la latencia conversacional del Swarm sin aumentar agresivamente el tamaño del modelo, se debe emparejar un modelo orquestador (Draft Model) ligero con un agente de validación (Target Model), decodificando múltiples tokens paralelos por pasada en los ciclos locales.
- **Compresión Asimétrica PyramidKV:** Forzar explícitamente una estrategia de retención asimétrica de la caché KV para los modelos atencionales auxiliares. Requerimiento inquebrantable de descartar capas de poco valor reduciendo la retención al 12%, concentrando el contexto en las extremidades conceptuales.

## 2. Percepción Estructural Evolucionada
- **Sustitución de Árboles Sintácticos (AST):** Se prohíbe el uso de lecturas en texto plano para los motores deductivos y el escaneo AST tradicional por su carencia de semántica de flujo de datos.
- **Data Transformation Graphs (DTG):** agentOrquestor procesará únicamente sub-grafos semánticos DTG construidos bajo demanda. Los modelos percibirán el estado del IDE analizando las transformaciones y mutaciones puras de las variables, deduciendo el flujo y el linaje de los datos sin verse abrumados por el ruido del "boiler plate" de las librerías, ahorrando crucial y exponencial memoria de abstracción.

## 3. Sandboxing Formal y E/S Sub-Milisegundo
- **WebAssembly (Wasm) Runtime:** Todo plan de código volátil propuesto por el enjambre o la extensión de herramientas MCP transita estrictamente pre-compilado en runtimes encapsulados de `Wasm`.
- **Certificación Z3:** Los nodos lógicos del orquestador exigirán demostración SMT mediante el Verificador Lógico `Z3` antes de la ejecución de rutinas (Comprobación de invariables de tipo de datos y restricciones de seguridad).
- **Latencia Zero-Copy (io_uring y eBPF):** La observación telemétrica del estado del IDE y los flujos hacia Wasm se operan instrumentalmente inyectando trazadores directamente al kernel a través de `eBPF`, permitiendo lecturas asincrónicas extremas vía anillos `io_uring`, reduciendo a cero las llamadas ineficientes en userspace (syscall context switches).

## 4. Persistencia GraphRAG y Evolución Continua (Local LoRA)
- **Almacenamiento Concurrente C-Base:** Acople arquitectónico a bases concurrentes tipo `SQLite` operando en modo WAL para transacciones semánticas. 
- **GraphRAG:** Evolución del RAG escalar. Construcción de representaciones basadas en vértices e intenciones, donde los nodos persistidos codifican descripciones modulares de todo el espacio de trabajo local.
- **Aprendizaje Local (DPO y LoRA):** Los comentarios e iteraciones de los desarrolladores en el IDE actúan como "Feedback Signal". El orquestador sintetiza estos eventos en background para entrenar y re-acoplar adaptadores dinámicos `LoRA` utilizando Optimización Directa de Preferencias (DPO), calibrando el comportamiento táctico en futuras instancias.

## 5. Endurecimiento Ubuntu y Seguridad Nativa
- **Privilegio Userspace Estricto:** Restricción dogmática de solicitudes de elevación a `root`. El demonio corre de forma confinada utilizando dominios AppArmor, previniendo fuga desde el contenedor Wasm y el orquestador principal.
- **Políticas de Aislamiento de Flujo:** Obligación irrestrictamente paralela para las tareas del Swarm de ramificar el árbol Git (`git checkout -b local_swarm_uuid`). Los agentes asumen estado temporal en los nodos de decisión y toda confirmación mutativa requiere auditoría o "Merge Formal".
