import sys
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from core.event_bus import bus

class LightweightChronicler:
    """
    El Hipocampo: Memoria Semántica de Bajo Consumo (Pure NumPy).
    Evita cargar bases de datos pesadas en RAM/VRAM.
    """
    def __init__(self, db_path="memory/graph/chronicler_vdb.json"):
        self.db_path = db_path
        self.memory = []
        self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                self.memory = json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self.memory, f)

    async def log_success(self, data: Dict[str, Any]):
        """Registra un par [Problema + Error] -> [Solución]."""
        entry = {
            "task": data.get("task", ""),
            "error": data.get("error", "None"),
            "solution": data.get("solution", ""),
            "timestamp": "2026-03-10"
        }
        self.memory.append(entry)
        self._save()
        sys.stderr.write(f"📖 [CHRONICLER] Memoria episódica guardada: {entry["task"][:30]}..." + \"\n\")

    def query(self, query_text: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Búsqueda simple por coincidencia de palabras (Sin embeddings pesados en VRAM)."""
        # En una versión avanzada, usaríamos un modelo de embedding en el i9 (CPU)
        results = []
        query_words = set(query_text.lower().split())
        for entry in self.memory:
            entry_words = set(entry["task"].lower().split()) | set(entry["error"].lower().split())
            score = len(query_words & entry_words)
            if score > 0:
                results.append((score, entry))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]

chronicler = LightweightChronicler()

# Suscripción al bus para aprendizaje automático
bus.subscribe("CODE_IMPLEMENTED", chronicler.log_success)