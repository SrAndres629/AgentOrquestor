import json
import os
from datetime import datetime
from typing import Dict, Any, List
from core.telemetry import telemetry

class Chronicler:
    """
    Sistema de Memoria Episódica v4.0.
    Almacena lecciones aprendidas de debates y ejecuciones del Sandbox.
    """
    def __init__(self, storage_path: str = ".cortex/knowledge/lessons.jsonl"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def record_lesson(self, mission_id: str, goal: str, outcome: Dict[str, Any]):
        """
        Guarda un registro de lo aprendido.
        """
        lesson = {
            "timestamp": datetime.now().isoformat(),
            "mission_id": mission_id,
            "goal": goal,
            "success": outcome.get("status") == "SUCCESS",
            "error_log": outcome.get("stderr", ""),
            "fix_applied": outcome.get("status") == "SUCCESS"
        }
        
        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(lesson) + "\n")
            telemetry.info(f"📖 Chronicler: Nueva lección archivada para '{goal[:30]}...'")
        except Exception as e:
            telemetry.error(f"❌ Chronicler: Error al persistir lección: {e}")

    def get_relevant_lessons(self, current_goal: str) -> List[Dict[str, Any]]:
        """
        Búsqueda simple (keyword-based) de lecciones previas.
        """
        if not os.path.exists(self.storage_path):
            return []

        lessons = []
        keywords = set(current_goal.lower().split())
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    lesson = json.loads(line)
                    lesson_goal = lesson["goal"].lower()
                    if any(kw in lesson_goal for kw in keywords):
                        lessons.append(lesson)
        except Exception:
            return []
        
        return lessons[:3]

chronicler = Chronicler()
