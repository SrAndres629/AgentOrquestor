"""
AgentOrquestor — Mission Planner (Strategic Cortex) v5.0
=========================================================
Audita el objetivo, evalúa capacidades (MCP/Skills) y coordina
la ignición del enjambre. Implementa las Leyes Metacognitivas.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.telemetry import telemetry
from core.perception import perception

BASE_DIR = Path(__file__).parent.parent
REGISTRY_PATH = BASE_DIR / "agents" / "registry.yaml"

class MissionPlanner:
    def __init__(self):
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        if not REGISTRY_PATH.exists():
            return {}
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def audit_capabilities(self, goal: str) -> Dict[str, Any]:
        """
        Analiza si el arsenal actual (MCP/Skills) es suficiente.
        Si faltan capacidades críticas, activa 'Misión Cero'.
        """
        goal_lower = goal.lower()
        missing_tools = []
        
        # Heurísticas de capacidad (Bootstrap Detection)
        capabilities = {
            "browser": ["puppeteer", "browser", "web", "scraping", "search"],
            "filesystem": ["file", "disk", "write", "read", "read_file", "write_file", "filesystem"],
            "security": ["scan", "audit", "exploit", "security", "vulnerability"],
            "network": ["request", "api", "endpoint", "traffic", "http", "fetch"],
            "database": ["sql", "postgres", "sqlite", "database", "query", "supabase"],
            "image": ["generate_image", "vision", "ocr", "image", "stable diffusion"]
        }
        
        # Obtener todas las herramientas cargadas en el registry
        all_loaded_tools = []
        for agent_cfg in self.registry.get("agents", {}).values():
            all_loaded_tools.extend(agent_cfg.get("tools", []))
        
        telemetry.info(f"🔍 Auditoría de Capacidades: {len(set(all_loaded_tools))} herramientas en arsenal.")

        # Identificar necesidades implícitas
        for cap, keywords in capabilities.items():
            if any(k in goal_lower for k in keywords):
                # Verificar si algún agente tiene herramientas para esta capacidad
                has_cap = False
                for t in all_loaded_tools:
                    if any(k in t.lower() for k in keywords):
                        has_cap = True
                        break
                
                if not has_cap:
                    missing_tools.append(cap)

        if missing_tools:
            telemetry.warning(f"🚧 Capacidad faltante detectada: {missing_tools}. Sugiriendo Misión Cero.")
            return {
                "bootstrap_needed": True,
                "missing_capabilities": missing_tools,
                "strategy": "M_0_BOOTSTRAP"
            }
        
        return {"bootstrap_needed": False, "strategy": "DIRECT_IGNITION"}

    def create_bootstrap_mission(self, original_goal: str, missing: List[str]) -> str:
        """Genera el prompt para la misión de autofabricación."""
        tools_list = ", ".join(missing)
        return (
            f"Misión Cero: Autofabricación de Capacidades.\n"
            f"El usuario desea: '{original_goal}'.\n"
            f"BLOQUEO: Faltan herramientas para: {tools_list}.\n"
            f"TAREA: Diseña y programa un servidor MCP o un Skill de AgentOrquestor "
            f"que proporcione estas capacidades. Al finalizar, utiliza la herramienta "
            f"`register_new_tool` para que el sistema aprenda a usar tu creación."
        )

    def register_tool(self, agent_name: str, tool_name: str):
        """
        Registra una nueva herramienta en el registry.yaml de forma persistente.
        """
        registry = self._load_registry()
        if "agents" not in registry:
            registry["agents"] = {}
        
        if agent_name in registry["agents"]:
            if "tools" not in registry["agents"][agent_name]:
                registry["agents"][agent_name]["tools"] = []
            if tool_name not in registry["agents"][agent_name]["tools"]:
                registry["agents"][agent_name]["tools"].append(tool_name)
                telemetry.info(f"🆕 [PLANNER] Herramienta '{tool_name}' registrada para {agent_name}.")
        
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            yaml.dump(registry, f, allow_unicode=True)
            
        # Forzar recarga interna
        self.registry = registry

planner = MissionPlanner()
