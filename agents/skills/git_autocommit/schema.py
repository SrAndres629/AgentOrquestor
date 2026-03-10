from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ZeroTrustTelemetry(BaseModel):
    """
    Certificación de pre-condiciones formales para ejecución segura temporal.
    Requerido inquebrantablemente por la capa `core` de AgentOrquestor.
    """
    ebpf_trace_id: str = Field(..., description="Identificador circular de rastreo en espacio de Kernel (io_uring).")
    z3_invariant_verified: bool = Field(..., description="Certificación de demostración libre de conflictos (Merge).")


class GitCommitPayload(BaseModel):
    """
    Datos de entrada (DTO) para la operación Git (Zero-Copy a Wasm simulado).
    """
    commit_message: Optional[str] = Field(None, description="Mensaje Semántico pre-procesado por el Swarm. De ser None, autogenera convencionalmente.")
    push_remote: bool = Field(True, description="Indicador binario para ejecutar sync remoto después del commit.")
    target_branch: Optional[str] = Field(None, description="Rama remota explícita. Omitir para aserción nativa local.")


class GitAutocommitContract(BaseModel):
    """
    Esquema principal de Validación del Payload (URN: urn:agent-orquestor:skill:schema:v1:base)
    Cruza las fronteras Pydantic al invocar a la habilidad "git_autocommit".
    """
    skill_id: str = Field(..., description="UUID Determinista de la Skill.")
    intent_context: str = Field(..., description="Contexto Semántico del Grafo (Fallback Router).")
    payload: GitCommitPayload = Field(..., description="Variables del proceso aislado de Git.")
    zero_trust_telemetry: ZeroTrustTelemetry = Field(..., description="Firma de confianza estricta de hardware/matemática.")
