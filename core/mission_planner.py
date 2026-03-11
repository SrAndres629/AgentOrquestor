import json
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class MissionManifest(BaseModel):
    """Esquema de misión para el OSAA v4.0."""
    mission_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    agents: List[str] = ["LeadDev", "SecurityQA"]
    constraints: Dict[str, Any] = {
        "max_vram_mb": 5800,
        "max_tokens": 4000,
        "dialectic_rounds": 3
    }
    steps: List[str]
    status: str = "PLANNED"

class MissionPlanner:
    """
    Abstracción de Nivel 0.
    Genera el Manifiesto de Misión a partir de lenguaje natural.
    """
    def __init__(self):
        self.default_model = "gemini-2.0-flash"

    def create_manifest(self, user_order: str, tasks: List[str]) -> MissionManifest:
        """Crea un manifiesto estructurado para la misión."""
        return MissionManifest(
            goal=user_order,
            steps=tasks
        )

if __name__ == "__main__":
    planner = MissionPlanner()
    manifest = planner.create_manifest(
        "Refactorizar el sistema de archivos del OSAA",
        ["Auditar redundancia", "Mover bloatware a Unidad D", "Verificar integridad"]
    )
    print(manifest.model_dump_json(indent=2))
