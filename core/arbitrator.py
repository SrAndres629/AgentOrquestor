import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set
from core.telemetry import telemetry

def _normalize_claim(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[`*_>#\[\]():;]', ' ', s)
    return s

class Arbitrator:
    """
    Motor de Consenso Dialéctico v4.0.
    Mide la convergencia entre Tesis (LeadDev) y Antítesis (SecurityQA).
    """
    def __init__(self, threshold: float = 0.90, plateau_rounds: int = 2):
        self.threshold = threshold
        self.plateau_rounds = plateau_rounds
        self.history = []
        self._negations = ('no ', 'nunca', 'sin ', 'reject', 'vulnerabilidad', 'riesgo', 'fail')

    def extract_claims(self, text: str) -> List[str]:
        claims = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(('-', '*', '•', '1.', '2.')) or len(line) > 20:
                claims.append(line.lstrip('-*•123456789. ').strip())
        return [c for c in claims if len(c) > 10]

    def calculate_convergence(self, pro_text: str, adv_text: str) -> float:
        pro_claims = self.extract_claims(pro_text)
        adv_claims = self.extract_claims(adv_text)
        pro_set = {_normalize_claim(c) for c in pro_claims}
        adv_set = {_normalize_claim(c) for c in adv_claims}
        intersection = len(pro_set & adv_set)
        union = len(pro_set | adv_set)
        overlap = intersection / union if union > 0 else 0.0
        contradictions = 0
        for c in adv_claims:
            norm = _normalize_claim(c)
            if any(neg in norm for neg in self._negations):
                contradictions += 1
        contra_ratio = contradictions / len(adv_claims) if adv_claims else 0.0
        score = max(0.0, min(1.0, (overlap * 0.7) + ((1.0 - contra_ratio) * 0.3)))
        self.history.append(score)
        telemetry.info(f'Arbitraje: Score {score:.4f} (Solapamiento: {overlap:.2f}, Riesgo: {contra_ratio:.2f})')
        return score

    def is_stable(self) -> bool:
        if len(self.history) < self.plateau_rounds:
            return False
        recent = self.history[-self.plateau_rounds:]
        return max(recent) >= self.threshold and (max(recent) - min(recent)) < 0.02

arbitrator = Arbitrator()
