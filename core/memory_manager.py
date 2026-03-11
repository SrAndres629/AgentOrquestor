import sys
import os
import json
import time
import uuid
import hashlib
from typing import Dict, Any, List
from core.event_bus import bus
from core.telemetry import telemetry

class CortexVault:
    """
    El Registro de Existencia: Gestiona la persistencia desacoplada del AgentOrquestor.
    Ubicación: .cortex/
    """
    def __init__(self, base_path=".cortex"):
        self.base_path = base_path
        self.snapshot_path = f"{base_path}/snapshots"
        self.embedding_path = f"{base_path}/embeddings"
        self.multimodal_path = f"{base_path}/multimodal"
        os.makedirs(self.snapshot_path, exist_ok=True)
        os.makedirs(self.embedding_path, exist_ok=True)
        os.makedirs(self.multimodal_path, exist_ok=True)

    def _task_id_from_objective(self, objective: str) -> str:
        objective = objective or ""
        return hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12] if objective else "unknown"

    async def save_consciousness_manifesto(self, state_data: Dict[str, Any]):
        """
        Genera el "Save Game" semántico (Brain Handover).
        Se dispara antes de una rotación de modelo por cuota.
        """
        manifesto = {
            "timestamp": time.time(),
            "mission_objective": state_data.get("task_manifest", {}).get("objective", ""),
            "last_technical_intuition": state_data.get("dtg_context", {}).get("last_thought", "N/A"),
            "critical_blockers": state_data.get("dtg_context", {}).get("blockers", []),
            "current_architecture_focus": state_data.get("dtg_context", {}).get("active_file", "root")
        }

        task_id = self._task_id_from_objective(str(manifesto.get("mission_objective") or ""))
        manifesto["task_id"] = task_id
        
        filename = f"manifesto_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
        shard_dir = os.path.join(self.snapshot_path, task_id)
        os.makedirs(shard_dir, exist_ok=True)
        path = os.path.join(shard_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifesto, f, indent=4)
        
        sys.stderr.write(f"🧠 [CORTEX] Manifiesto de Conciencia guardado en snapshots/{task_id}/{filename}\n")
        telemetry.emit_event(
            "CORTEX_MANIFESTO_SAVED",
            {"filename": filename, "objective": manifesto["mission_objective"], "task_id": task_id},
        )
        return manifesto

    def retrieve_relevant_memory(self, query: str) -> List[Dict[str, Any]]:
        """Recupera fragmentos de memoria técnica para el nuevo modelo."""
        query_words = {w for w in query.lower().split() if len(w) >= 3}
        if not query_words:
            return []

        try:
            files: List[str] = []
            for entry in os.listdir(self.snapshot_path):
                path = os.path.join(self.snapshot_path, entry)
                if os.path.isfile(path) and path.endswith(".json"):
                    files.append(path)
                elif os.path.isdir(path):
                    try:
                        for f in os.listdir(path):
                            fp = os.path.join(path, f)
                            if os.path.isfile(fp) and fp.endswith(".json"):
                                files.append(fp)
                    except Exception:
                        continue
        except Exception:
            return []

        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        hits: List[Dict[str, Any]] = []
        for path in files[:200]:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                objective = str(obj.get("mission_objective", "")).lower()
                words = set(objective.split())
                if query_words & words:
                    obj["_path"] = path
                    hits.append(obj)
                    if len(hits) >= 3:
                        break
            except Exception:
                continue
        return hits

vault = CortexVault()
