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
        messages = state.get('messages', [])
        total_chars = sum(len(m.content) for m in messages if hasattr(m, 'content'))
        
        if total_chars / 4 > self.token_threshold:
            sys.stderr.write(f'✂️ [SHREDDER] Alerta de Contexto: {int(total_chars/4)} tokens.' + \"\n\")
            task_obj = state.get('task_manifest', {}).get('objective', 'Tarea desconocida')
            shredded_content = f'[CONTEXT SHREDDED] Objective: {task_obj}'
            
            await bus.publish('CONTEXT_SHREDDED', data={'original': int(total_chars/4)})
            sys.stderr.write('✨ [SHREDDER] Contexto destilado para RTX 3060.' + \"\n\")
            return True
        return False

shredder = AdvancedContextShredder()
