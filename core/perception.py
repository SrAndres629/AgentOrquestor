import os
import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from core.hardware_monitor import HardwareMonitor
from core.telemetry import telemetry

hardware_monitor = HardwareMonitor()

class PerceptionEngine:
    """
    Destila e inyecta las guías OSAA v6.0 en el córtex de los agentes aislados.
    Garantiza que el hardware (6GB VRAM) y las leyes termodinámicas se respeten.
    """
    def __init__(self, workspace_root: str = None):
        if workspace_root is None:
            # Detectar raíz del proyecto
            workspace_root = Path(__file__).resolve().parent.parent
        self.guides_dir = Path(workspace_root) / "docs" / "guides"

    def _read_guide(self, filename: str) -> str:
        path = self.guides_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        telemetry.warning(f"[PerceptionEngine] Guía no encontrada: {filename}")
        return ""

    def assemble_mind(self, agent_name: str) -> str:
        """Ensambla el System Prompt estricto basado en la identidad del agente."""
        core_mind = []
        
        # 1. Leyes Universales (Sobrevivir en tmux, truncar herramientas, razonamiento, etc)
        core_mind.append(self._read_guide("00_meta_guide_protocol.md")) # Base v6.0
        core_mind.append(self._read_guide("01_worker_protocol.md"))
        core_mind.append(self._read_guide("02_cognitive_cortex.md")) # Córtex Lógico mandatorio
        core_mind.append(self._read_guide("04_tool_blueprint.md"))
        
        # 2. Conciencia de Expansión (Guías 07-16)
        # Buscamos todas las guías de la 07 a la 16
        for i in range(7, 17):
            # Buscar el archivo que empieza por el número
            matches = list(self.guides_dir.glob(f"{i:02d}_*.md"))
            if matches:
                core_mind.append(matches[0].read_text(encoding="utf-8"))

        # 3. Especialización Genética
        if "Seed" in agent_name or "Bootstrap" in agent_name:
            core_mind.append(self._read_guide("03_bootstrap_protocol.md"))
        
        if "Security" in agent_name or "Auditor" in agent_name or "Warden" in agent_name:
            core_mind.append(self._read_guide("09_inquisidor_protocol.md"))

        # Unir con separadores fuertes para la atención del LLM
        return "\n\n" + "="*50 + "\n[OSAA v6.0 CONSTITUTIONAL CORE]\n" + "="*50 + "\n\n" + "\n\n".join(filter(None, core_mind))

class PerceptionNode:
    """
    Lóbulo Frontal v6.0 (Evolucionado).
    Génesis y Estrategia Metabólica (Guía 00/06).
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
        
        # 1. Selección de Modo (Filtro de Supervivencia)
        if available_vram < self.threshold_vram_low:
            mode = "FAST"
            justification = "VRAM Crítica detectada. Modo Supervivencia activo."
        elif any(kw in user_goal.lower() for kw in ["refactor", "optimizar", "core", "audit"]):
            mode = "SLOW"
            justification = "Complejidad Estructural detectada. Requiere pensamiento lento."
        else:
            mode = "FAST"
            justification = "Objetivo estándar detectado. Optimizando para velocidad."

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
        if "registry" in goal.lower(): variables.append("Integridad de Herramientas")
        return variables

perception = PerceptionNode()
engine = PerceptionEngine()
