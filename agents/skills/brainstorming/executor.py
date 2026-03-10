import os
from core.event_bus import bus

class BrainstormingExecutor:
    async def run_socratic_design(self, idea: str):
        print(f'🧠 [BRAINSTORM] Iniciando diseño socrático para: {idea}')
        return True

executor = BrainstormingExecutor()
