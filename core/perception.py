import json
from typing import Dict, Any, List
from core.hardware_monitor import HardwareMonitor
from core.chronicler import chronicler
from core.telemetry import telemetry

hardware_monitor = HardwareMonitor()

class PerceptionNode:
    """
    Lóbulo Frontal v5.0 (Evolucionado).
    Actúa como Estratega de Recursos y Generador de Contratos Cognitivos.
    """
    def __init__(self):
        self.threshold_vram_low = 2000  # MB
        self.complexity_map = {
            "FAST": {"desc": "Heurístico", "token_limit": 1000, "rounds": 2, "doubt": "OPTIMIZACIÓN"},
            "SLOW": {"desc": "Deductivo", "token_limit": 3000, "rounds": 4, "doubt": "INQUISIDOR"}
        }

    def analyze_situation(self, user_goal: str) -> Dict[str, Any]:
        """
        Analiza el hardware y define el Modo de Razonamiento y el Contrato Cognitivo.
        """
        hw_stats = hardware_monitor.check_stability()
        available_vram = hw_stats["vram"]["vram_total"] - hw_stats["vram"]["vram_used"]
        
        # 1. Análisis de Precedentes
        past_lessons = chronicler.get_relevant_lessons(user_goal)
        has_precedent = len(past_lessons) > 0

        # 2. Selección de Modo (Filtro de Supervivencia)
        if available_vram < self.threshold_vram_low:
            mode = "FAST"
            justification = "VRAM Crítica detectada. Modo Supervivencia activo."
        elif not has_precedent or any(kw in user_goal.lower() for kw in ["refactor", "optimizar", "core"]):
            mode = "SLOW"
            justification = "Complejidad Estructural detectada. Requiere pensamiento lento."
        else:
            mode = "FAST"
            justification = "Patrón conocido detectado. Optimizando para velocidad."

        # 3. Generación del Contrato Cognitivo (Framing)
        contract = self.generate_cognitive_contract(mode, available_vram)

        perception_snapshot = {
            "mode": mode,
            "justification": justification,
            "contract": contract,
            "variables_criticas": self._define_critical_variables(user_goal),
            "vram_context": available_vram
        }

        telemetry.info(f"🧠 Percepción: Contrato {mode} generado. Presupuesto: {contract['max_rounds_budget']} rondas.")
        return perception_snapshot

    def generate_cognitive_contract(self, mode: str, vram: float) -> Dict[str, Any]:
        """
        Define los límites de gasto metabólico y agresividad dialéctica.
        """
        config = self.complexity_map[mode]
        
        # Ajuste dinámico de rondas según VRAM real
        rounds_budget = config["rounds"]
        if vram < 1500: rounds_budget = 1 # Veto absoluto a debates largos
        
        return {
            "max_tokens_allowed": config["token_limit"],
            "max_rounds_budget": rounds_budget,
            "doubt_level": config["doubt"],
            "metabolic_priority": "EFFICIENCY" if vram < 2500 else "PERFORMANCE"
        }

    def _define_critical_variables(self, goal: str) -> List[str]:
        """Encuadre: Identifica sobre qué debe enfocarse el agente."""
        variables = ["Estabilidad VRAM", "Consistencia del Event Bus"]
        if "chronicler" in goal.lower(): variables.append("Integridad de Memoria")
        if "sandbox" in goal.lower(): variables.append("Seguridad de Ejecución")
        return variables

perception = PerceptionNode()
