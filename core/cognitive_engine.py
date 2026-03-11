import json
from typing import Dict, Any, List
from core.hardware_monitor import HardwareMonitor
from core.chronicler import Chronicler
from core.telemetry import telemetry

hardware_monitor = HardwareMonitor()
chronicler = Chronicler()

class CognitiveEngine:
    """
    Motor de Modelos Mentales OSAA v4.0.
    Gestiona Heurística, ToT y Deducción Lógica.
    """
    def __init__(self):
        self.heuristics = {
            "vram_low": 2000,
            "vram_critical": 500
        }

    def apply_heuristics(self, state_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Nivel 1: Pensamiento Rápido (System 1).
        Decide la estrategia basada en recursos y memoria histórica.
        """
        # 1. Telemetría en Tiempo Real
        hw_stats = hardware_monitor.check_stability()
        vram_available = hw_stats["vram"]["vram_total"] - hw_stats["vram"]["vram_used"]
        
        # 2. Consulta de Lecciones Aprendidas (Chronicler)
        user_goal = state_context.get("mission_goal", "")
        past_lessons = chronicler.get_relevant_lessons(user_goal)
        
        # 3. Síntesis Heurística
        strategy = {
            "complexity_level": "HIGH" if vram_available > self.heuristics["vram_low"] else "LOW",
            "vram_headroom": vram_available,
            "avoid_patterns": [l["error_log"] for l in past_lessons if not l["success"]],
            "proven_paths": [l["fix_applied"] for l in past_lessons if l["success"]]
        }
        
        telemetry.info(f"🧠 Cognición: Estrategia {strategy['complexity_level']} definida. (VRAM: {vram_available}MB)")
        return strategy

    def generate_tot_paths(self, goal: str, available_tools: List[Dict]) -> List[str]:
        """
        Nivel 2: Tree of Thoughts (Exploración).
        Genera 3 ramas de ejecución posibles antes de decidir.
        """
        # Simulación de pensamiento ramificado (En v5.0 esto usa LLM ligero)
        paths = [
            f"Ruta A: Ejecución directa con {available_tools[0]['name'] if available_tools else 'código nativo'}",
            "Ruta B: Análisis profundo y validación cruzada antes de actuar",
            "Ruta C: Descomposición recursiva en sub-agentes"
        ]
        telemetry.info(f"🌳 ToT: Explorando 3 ramas de pensamiento para '{goal[:20]}...'")
        return paths

    def validate_friction(self, pro_report: str, adv_report: str) -> bool:
        """
        Nivel 3: Antagonismo Dialéctico.
        Verifica si existe tensión real o si es 'cortesía algorítmica'.
        """
        if len(adv_report) < (len(pro_report) * 0.3):
            telemetry.warning("⚠️ Cognición: Crítica insuficiente. Se requiere más fricción.")
            return False
            
        tension_markers = ["?", "riesgo", "vulnerabilidad", "ineficiente", "error", "fallo", "latencia"]
        if not any(m in adv_report.lower() for m in tension_markers):
            telemetry.warning("⚠️ Cognición: Falta de cuestionamiento explícito en la antítesis.")
            return False
            
        return True

cognitive_engine = CognitiveEngine()
