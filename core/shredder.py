import sys
import asyncio
import re
from typing import List, Dict, Any
from core.event_bus import bus
from core.memory_manager import vault

class AdvancedContextShredder:
    def __init__(self, token_threshold=3000):
        self.token_threshold = token_threshold

    async def shred(self, state: Any):
        messages = getattr(state, "messages", None)
        if messages is None and isinstance(state, dict):
            messages = state.get("messages", [])
        messages = messages or []

        total_chars = 0
        for m in messages:
            content = getattr(m, "content", None)
            if content:
                total_chars += len(str(content))
        
        if total_chars / 4 > self.token_threshold:
            sys.stderr.write(f"✂️ [SHREDDER] Alerta de Contexto: {int(total_chars/4)} tokens.\n")
            task_manifest = getattr(state, "task_manifest", None)
            task_obj = getattr(task_manifest, "objective", None) if task_manifest else None
            if not task_obj and isinstance(state, dict):
                task_obj = state.get("task_manifest", {}).get("objective")
            task_obj = task_obj or "Tarea desconocida"
            
            await bus.publish("CONTEXT_SHREDDED", data={"original_tokens": int(total_chars / 4)})
            sys.stderr.write("✨ [SHREDDER] Contexto destilado para RTX 3060.\n")
            return True
        return False

shredder = AdvancedContextShredder()
