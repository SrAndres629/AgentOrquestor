"""
AgentOrquestor — Chronicler (Long-term Memory & Personality) v5.0
================================================================
Consolida la personalidad del sistema y persiste la evolución
del arsenal técnico.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.telemetry import telemetry

BASE_DIR = Path(__file__).parent.parent
MEMORY_VAULT = BASE_DIR / ".cortex" / "memory_vault.jsonl"

class Chronicler:
    def __init__(self):
        MEMORY_VAULT.parent.mkdir(parents=True, exist_ok=True)
        if not MEMORY_VAULT.exists():
            MEMORY_VAULT.touch()

    def remember_tool_creation(self, tool_name: str, purpose: str, mission_id: str):
        """Registra la creación de una nueva herramienta para usos futuros."""
        entry = {
            "ts": time.time(),
            "type": "TOOL_FABRICATION",
            "tool_name": tool_name,
            "purpose": purpose,
            "mission_id": mission_id,
            "learned_from": "OSAA_EVOLUTIONARY_LOOP"
        }
        self._append_to_vault(entry)
        telemetry.info(f"🧠 Memoria: Recordando herramienta '{tool_name}' forjada en misión {mission_id}.")

    def remember_mission(self, mission_id: str, status: str, summary: str):
        """Persiste el resultado de una misión como lección aprendida."""
        entry = {
            "ts": time.time(),
            "type": "MISSION_LESSON",
            "mission_id": mission_id,
            "status": status,
            "summary": summary
        }
        self._append_to_vault(entry)

    def _append_to_vault(self, entry: Dict[str, Any]):
        with open(MEMORY_VAULT, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_recent_skills(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Recupera las habilidades recientemente aprendidas/creadas."""
        entries = []
        if not MEMORY_VAULT.exists(): return entries
        
        with open(MEMORY_VAULT, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                data = json.loads(line)
                if data["type"] == "TOOL_FABRICATION":
                    entries.append(data)
                if len(entries) >= limit: break
        return entries

chronicler = Chronicler()
