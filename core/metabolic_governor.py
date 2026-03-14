import os
import json
import time
import fcntl
from typing import Dict, Any, Optional
from core.telemetry import telemetry

class MetabolicGovernor:
    """
    Controlador de Costos Metabólicos (Token-to-Dollar) v6.0.
    Gestiona el presupuesto de las misiones y el consumo de los modelos.
    """
    
    # Precios por 1M de tokens (USD) - Octubre 2024 aprox.
    # [Input/Context, Output/Generated]
    PRICE_MAP = {
        "llama-3.3-70b-versatile": [0.59, 0.79],
        "llama-3.1-8b-instant": [0.05, 0.08],
        "mixtral-8x7b-32768": [0.27, 0.27],
        "claude-3-5-sonnet-latest": [3.00, 15.00],
        "claude-3-opus-latest": [15.00, 75.00],
        "gemini-1.5-pro-latest": [3.50, 10.50],
        "gemini-1.5-flash-latest": [0.075, 0.30],
        "gpt-4o": [5.00, 15.00],
    }

    def __init__(self, ledger_path: str = ".cortex/metabolic_ledger.json"):
        self.ledger_path = ledger_path
        self._load_ledger()

    def _load_ledger(self):
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r") as f:
                    self.data = json.load(f)
            except:
                self.data = {"missions": {}, "global_total": 0.0}
        else:
            self.data = {"missions": {}, "global_total": 0.0}

    def _save_ledger(self):
        import fcntl
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            fcntl.lockf(f, fcntl.LOCK_EX)
            json.dump(self.data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.lockf(f, fcntl.LOCK_UN)

    def calculate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Calcula el costo en USD basándose en el modelo y el volumen."""
        prices = self.PRICE_MAP.get(model.lower(), [1.0, 2.0]) # Default fallback costoso para seguridad
        cost_in = (tokens_in / 1_000_000) * prices[0]
        cost_out = (tokens_out / 1_000_000) * prices[1]
        return cost_in + cost_out

    def record_consumption(self, mission_id: str, agent: str, model: str, tokens_in: int, tokens_out: int):
        """Registra el gasto de una inferencia."""
        cost = self.calculate_cost(model, tokens_in, tokens_out)
        
        if mission_id not in self.data["missions"]:
            self.data["missions"][mission_id] = {"total_usd": 0.0, "agents": {}, "budget_limit": 1.0}
            
        mission = self.data["missions"][mission_id]
        mission["total_usd"] += cost
        self.data["global_total"] += cost
        
        if agent not in mission["agents"]:
            mission["agents"][agent] = {"usd": 0.0, "tokens_in": 0, "tokens_out": 0}
            
        mission["agents"][agent]["usd"] += cost
        mission["agents"][agent]["tokens_in"] += tokens_in
        mission["agents"][agent]["tokens_out"] += tokens_out
        
        self._save_ledger()
        telemetry.info(f"💰 [METABOLIC] {agent} consumió ${cost:.6f} ({model}). Misión: ${mission['total_usd']:.4f}")

    def check_health(self, mission_id: str) -> Dict[str, Any]:
        """Verifica si la misión está dentro del presupuesto."""
        mission = self.data["missions"].get(mission_id, {"total_usd": 0.0, "budget_limit": 1.0})
        status = "HEALTHY"
        if mission["total_usd"] >= mission["budget_limit"] * 0.8:
            status = "CONGESTED"
        if mission["total_usd"] >= mission["budget_limit"]:
            status = "STARVING"
            
        return {
            "status": status,
            "used_usd": mission["total_usd"],
            "limit_usd": mission["budget_limit"],
            "percent": (mission["total_usd"] / mission["budget_limit"]) * 100 if mission["budget_limit"] > 0 else 0
        }

mcu = MetabolicGovernor()
