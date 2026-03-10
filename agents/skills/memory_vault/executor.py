import json
import os
import hashlib
from typing import Dict, Any
from core.telemetry import telemetry

class MemoryVaultExecutor:
    """Sincronizador Multimodal de Bóveda (.cortex)."""
    def __init__(self, cortex_path=".cortex"):
        self.cortex_path = cortex_path

    def sync_entry(self, task: str, code: str, image_path: str = None):
        """Indexa texto y hash de imágenes para persistencia."""
        entry_id = hashlib.sha256(task.encode()).hexdigest()[:12]
        
        # Guardar en multimodal si hay imagen
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Indexación cruzada
            meta = {
                "id": entry_id,
                "task": task,
                "image_hash": img_hash,
                "code_ref": code[:100]
            }
            
            os.makedirs(os.path.join(self.cortex_path, "multimodal"), exist_ok=True)
            path = os.path.join(self.cortex_path, "multimodal", f"index_{entry_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(meta, f)
            
            telemetry.info(f"✨ [SKILL] Memoria Multimodal Sincronizada: {entry_id}")
        return entry_id

executor = MemoryVaultExecutor()
