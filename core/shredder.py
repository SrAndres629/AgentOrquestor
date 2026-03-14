import re
from typing import Dict, Any, List
from core.telemetry import telemetry

class LogShredder:
    """
    Chronicler Protocol v6.0 (El Destilador de Memoria).
    Implementa la Guía 05 para evitar el colapso de la ventana de contexto.
    Realiza 'Context Distillation' agresiva para proteger los 6GB de VRAM.
    """
    def __init__(self, max_tokens_proxy: int = 1500):
        self.max_tokens_proxy = max_tokens_proxy
        self.noise_patterns = [
            r'DEBUG:.*',
            r'INFO:root:.*',
            r'\[.*\] .*:.*',
            r'HTTP Request:.*',
            r'{"timestamp":.*',  # JSON estructural de eventos
            r'202\d-\d\d-\d\d \d\d:.*' # Timestamps de logs
        ]

    def distill(self, raw_history: List[Dict[str, str]]) -> str:
        if not raw_history:
            return 'Estado: Inicial (Sin historial).'

        distilled_blocks = []
        for i, turn in enumerate(raw_history):
            pro = self._extract_essence(turn.get('proponent', ''))
            adv = self._extract_essence(turn.get('adversary', ''))
            block = (f'--- RONDA {i+1} ---\n' 
                     f'[SÍNTESIS_PROPUESTA]: {pro}\n' 
                     f'[RIESGOS_DETECTADOS]: {adv}\n')
            distilled_blocks.append(block)

        full_distill = '\n'.join(distilled_blocks)
        if len(full_distill) > self.max_tokens_proxy * 4:
            telemetry.info('🧹 Shredder: Poda agresiva por límite metabólico.')
            return full_distill[-(self.max_tokens_proxy * 4):]
        return full_distill

    def _extract_essence(self, text: str) -> str:
        lines = text.splitlines()
        essence = []
        for line in lines:
            if any(re.match(p, line) for p in self.noise_patterns):
                continue
            if line.strip().startswith(('-', '*', '•', 'APPROVED', 'REJECTED', 'FIX')):
                essence.append(line.strip())
            elif 'def ' in line or 'class ' in line:
                essence.append(line.strip())
        return ' | '.join(essence[:10])

shredder = LogShredder()
