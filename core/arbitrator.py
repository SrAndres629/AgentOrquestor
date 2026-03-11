import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from core.telemetry import telemetry


_NEGATIONS = ("no ", "not ", "nunca", "jamás", "sin ", "reject", "rejected", "vetar", "veto", "risk", "vuln")


def _normalize_claim(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[`*_>#\[\]():;]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_claims(text: str, *, max_claims: int = 64) -> List[str]:
    """
    Extract a lightweight set of "claims" (assertions) from a report.
    Deterministic and cheap (no embeddings). Designed for RTX 3060 constraints.
    """
    if not text:
        return []

    chunks: List[str] = []
    # Prefer line-based bullets
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("-", "*", "•")):
            chunks.append(line.lstrip("-*•").strip())
        else:
            chunks.append(line)

    # Split long chunks into sentence-ish pieces
    pieces: List[str] = []
    for ch in chunks:
        parts = re.split(r"[.!?]\s+|\n+", ch)
        for p in parts:
            p = p.strip()
            if len(p) >= 12:
                pieces.append(p)

    seen: Set[str] = set()
    out: List[str] = []
    for p in pieces:
        norm = _normalize_claim(p)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(p.strip())
        if len(out) >= max_claims:
            break
    return out


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return float(inter) / float(union) if union else 0.0


def _contradiction_ratio(proponent_claims: List[str], adversary_claims: List[str]) -> float:
    """
    Cheap contradiction detector: counts adversary claims that look like vetos/negations.
    Returns ratio in [0,1].
    """
    if not adversary_claims:
        return 0.0
    neg = 0
    for c in adversary_claims:
        n = _normalize_claim(c)
        if any(k in n for k in _NEGATIONS):
            neg += 1
    return float(neg) / float(len(adversary_claims))


@dataclass
class Arbitrator:
    """
    Dialectic consensus supervisor (KT-RPS):
    - Measures convergence between Proponent vs Adversary
    - Decides stability based on score threshold + plateau (epsilon) + max rounds
    """

    threshold: float = 0.92
    epsilon: float = 0.01
    plateau_rounds: int = 2
    history: List[Dict[str, Any]] = field(default_factory=list)

    def calculate_convergence(self, proponent_resp: str, adversary_audit: str) -> float:
        pro_claims = extract_claims(proponent_resp)
        adv_claims = extract_claims(adversary_audit)

        pro_set = {_normalize_claim(c) for c in pro_claims}
        adv_set = {_normalize_claim(c) for c in adv_claims}

        overlap = _jaccard(pro_set, adv_set)
        contradiction = _contradiction_ratio(pro_claims, adv_claims)

        # Stability proxy: reward overlap, penalize contradictions.
        # Range stays in [0,1].
        score = max(0.0, min(1.0, 0.6 * overlap + 0.4 * (1.0 - contradiction)))

        self.history.append(
            {
                "overlap": overlap,
                "contradiction": contradiction,
                "score": score,
                "pro_claims": len(pro_claims),
                "adv_claims": len(adv_claims),
            }
        )

        telemetry.emit_event(
            "DIALECTIC_CONVERGENCE",
            {"score": round(score, 4), "overlap": round(overlap, 4), "contradiction": round(contradiction, 4)},
        )
        return score

    def check_consensus(self, convergence: float) -> bool:
        if convergence < self.threshold:
            return False

        # Require plateau stability over last N rounds to avoid "alucinación de acuerdo"
        recent = [h["score"] for h in self.history[-self.plateau_rounds :]]
        if len(recent) < self.plateau_rounds:
            return False
        if max(recent) - min(recent) > self.epsilon:
            return False
        return True

    def maybe_compute_hki(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Optional: compute an HKI-like metric if numpy is available and enabled.
        This is a lightweight placeholder; consensus decisions remain proxy-based
        unless you explicitly wire HKI into check_consensus.
        """
        if os.getenv("ARBITRATOR_USE_HKI", "").strip() != "1":
            return False, {"enabled": False}
        try:
            import numpy as np  # type: ignore

            scores = np.array([h["score"] for h in self.history], dtype=float)
            if scores.size == 0:
                return True, {"enabled": True, "hki": None}
            # Proxy spectral stability: variance as "resistance" surrogate
            hki = float(np.var(scores))
            telemetry.emit_event("DIALECTIC_HKI_PROXY", {"variance": round(hki, 6)})
            return True, {"enabled": True, "hki_proxy_variance": hki}
        except Exception as e:
            return False, {"enabled": True, "error": str(e)}


arbitrator = Arbitrator()

