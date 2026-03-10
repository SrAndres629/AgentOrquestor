# Registro de Habilidades Bi-Direccionales (Skills Registry)

Este documento centraliza el contrato YAML base y las restricciones de formato (Schemas) requeridos para cualquier flujo bidireccional de herramientas integrado entre el Enjambre (Swarm), la red MCP (Model Context Protocol), y la capa E/S de base.

## Plantilla del Contrato de Metadatos Obligatorio (YAML)

Todas y cada una de las integraciones propuestas en los directorios de `mcp_servers` o `agents` requerirán la exposición de metadatos estandarizados para que el orquestador LangGraph clasifique su intención para el indexado en espacio semántico.

```yaml
version: "1.0-alpha"
namespace: "io.agentorquestor.skills.filesystem"
name: "mcp_tool_standard_template"
description: "Interacción de ejemplo altamente semántica; esta descripción se usará directamente para vectorizar intenciones en la base GraphRAG."
author: "agentOrquestor-v1"
capabilities:
  - type: "dtg_analysis"
    access_level: "read-only"
  - type: "wasm_exec"
    access_level: "isolated"
events:
  consumes:
    - "core.telemetry.ebpf_trigger"
  produces:
    - "sandbox.verification.completed"
constraints:
  timeout_ms: 100
  max_memory_mb: 64
```

## Esquema JSON de Validación del Payload (Pydantic v2)

Previo al tránsito y multiplexado a través de `io_uring`, todas las estructuras que crucen las fronteras del motor deben superar una serialización explícita, probada bajo formalismo `Z3` e instanciada con el motor `Pydantic v2`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:agent-orquestor:skill:schema:v1:base",
  "title": "AgentSkillExecutionContract",
  "type": "object",
  "properties": {
    "skill_id": {
      "type": "string",
      "format": "uuid",
      "description": "Identificador unívoco, determinista e inmutable para la rutina a invocar."
    },
    "intent_context": {
      "type": "string",
      "description": "Grafo de intenciones serializado (Semantic Router fallback string)."
    },
    "payload": {
      "type": "object",
      "description": "Datos de entrada (DTO mutables), canalizados de manera Zero-Copy hacia el entorno Wasm.",
      "additionalProperties": true
    },
    "zero_trust_telemetry": {
      "type": "object",
      "properties": {
        "ebpf_trace_id": {
          "type": "string",
          "description": "Identificador circular de rastreo en espacio de Kernel."
        },
        "z3_invariant_verified": {
          "type": "boolean",
          "description": "Certificación de pre-condiciones formales para ejecución segura temporal."
        }
      },
      "required": ["ebpf_trace_id", "z3_invariant_verified"]
    }
  },
  "required": [
    "skill_id",
    "intent_context",
    "payload",
    "zero_trust_telemetry"
  ]
}
```
