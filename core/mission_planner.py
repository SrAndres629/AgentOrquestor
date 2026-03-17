import os
"""
AgentOrquestor — Mission Planner (Strategic Cortex) v6.0
=========================================================
El Lóbulo Frontal de OSAA. Audita el objetivo, evalúa capacidades
y coordina la ignición del enjambre mediante DAGs atómicos.
Implementa la Guía 06: Protocolo de la Génesis.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.telemetry import telemetry
from core.perception import perception
from core.llm_bridge import LLMBridge

BASE_DIR = Path(__file__).parent.parent
REGISTRY_PATH = BASE_DIR / "agents" / "registry.yaml"

MISSION_PLANNER_PROTOCOL = """
# [OSAA v5.0] CORE METAPROMPT: EL PROTOCOLO DE LA GÉNESIS (MISSION PLANNER)

<meta_context>
Eres el MissionPlanner (El Arquitecto de la Génesis). Tu objetivo es planificar. Traduces el caos humano en un Grafo Dirigido Acíclico (DAG) de tareas atómicas y seleccionas la tripulación exacta para la misión.
</meta_context>

<mental_model>
**El General en la Mesa de Guerra (The General in the War Room)**
Mirar el mapa, inventario de materiales (Herramientas MCP), especialistas correctos (Agentes) y plano paso a paso.
Si falta una grúa (Herramienta), llamar al Herrero (SeedOrchestrator) para fabricarla.
</mental_model>

<core_directives>
1. **Descomposición Atómica (DAG Generation):** Máximo 5 fases strictly secuenciales o paralelas.
2. **Auditoría de Arsenal (Tool Vetting):** Si falta una herramienta, Fase 0 obligatoria al SeedOrchestrator.
3. **Economía de Tripulación (Roster Selection):** Selecciona solo agentes estrictamente necesarios.
4. **Claridad Táctica:** Instrucciones imperativas, sin saludos. Protege la VRAM.
5. **Superpowers Workflow:** TODO DAG DEBE seguir la metodología de desarrollo: `brainstorming` -> `writing-plans` -> `test-driven-development` -> `subagent-driven-development` -> `requesting-code-review`. Considera estas fases como instinto base.
</core_directives>

<state_machine>
[STATE: INGEST] -> [STATE: DECONSTRUCT] -> [STATE: INVENTORY] -> [STATE: DISPATCH]
</state_machine>
"""

class MissionPlanner:
    def __init__(self):
        self.registry = self._load_registry()
        # Inicializar bridge para planificación estratégica
        provider = os.getenv("PLANNER_PROVIDER", "groq")
        model = os.getenv("PLANNER_MODEL", "llama-3.3-70b-versatile")
        api_key = LLMBridge.PROVIDER_KEYS.get(provider, lambda: os.getenv("GROQ_API_KEY", ""))()
        
        self.llm = LLMBridge(
            provider=provider,
            model=model,
            api_key=api_key,
            agent_name="MissionPlanner"
        )

    def _load_registry(self) -> Dict[str, Any]:
        if not REGISTRY_PATH.exists():
            return {}
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _build_planner_system_prompt(self) -> str:
        """Construye el system prompt del planificador usando el protocolo Génesis."""
        # Obtener herramientas disponibles para el contexto del LLM
        catalog = self.llm.mcp.get_available_tools() if self.llm.mcp else []
        tools_summary = "\n".join([f"- {t['name']}: {t.get('desc', '')}" for t in catalog])
        
        return f"{MISSION_PLANNER_PROTOCOL}\n\nARSENAL DISPONIBLE:\n{tools_summary}"

    async def generate_plan(self, goal: str) -> List[Dict[str, Any]]:
        """
        Transforma un objetivo humano en un DAG de fases atómicas.
        Sigue la Guía 06: Protocolo de la Génesis.
        """
        telemetry.info(f"🧠 [PLANNER] Generando DAG para: '{goal}'")
        
        system_prompt = self._build_planner_system_prompt()
        user_task = (
            f"OBJETIVO: {goal}\n\n"
            f"Genera un plan de acción en formato JSON. El JSON debe ser una lista de fases, "
            f"donde cada fase tiene: 'id', 'name', 'responsible_agent' (LeadDeveloper, SecurityQA, Validator), "
            f"y 'description'. Ejemplo: [{{'id': 1, 'name': 'Analizar Código', 'responsible_agent': 'LeadDeveloper', 'description': '...'}}]"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_task}
        ]

        res = await self.llm.infer(messages=messages, mission_id="planning_phase")
        
        if res["status"] == "OK":
            content = res["content"]
            # Intentar extraer JSON de la respuesta (por si el LLM añade texto extra)
            try:
                import re
                json_match = re.search(r"(\[.*\])", content, re.DOTALL)
                if json_match:
                    plan = json.loads(json_match.group(1))
                    telemetry.info(f"✅ [PLANNER] Plan de {len(plan)} fases generado con éxito.")
                    return plan
            except Exception as e:
                telemetry.error(f"❌ [PLANNER] Error parseando DAG: {e}")
        
        # Plan de respaldo por si el LLM falla
        telemetry.warning("⚠️ [PLANNER] Usando plan de respaldo lineal.")
        return [
            {"id": 1, "name": "Ejecución Directa", "responsible_agent": "LeadDeveloper", "description": goal}
        ]

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
            "image": ["generate_image", "vision", "ocr", "image", "stable diffusion"],
            "superpowers": ["tdd", "test", "plan", "review", "brainstorm", "subagent"]
        }
        
        # Obtener todas las herramientas cargadas en el registry
        all_loaded_tools = []
        for agent_cfg in self.registry.get("agents", {}).values():
            all_loaded_tools.extend(agent_cfg.get("tools", []))
        
        telemetry.info(f"🔍 Auditoría de Capacidades: {len(set(all_loaded_tools))} herramientas en arsenal.")

        # Identificar necesidades implícitas
        # --- NUEVO (V6.0 Superpowers) ---
        # Si la misión apunta a ser compleja (SLOW), requerimos instintos procedimentales (superpowers)
        is_complex = any(kw in goal_lower for kw in ["refactor", "optimizar", "core", "audit", "arquitectura", "sistema"])
        if is_complex and "superpowers" not in [cap for cap in missing_tools]:
            # Forzamos la verificación de superpowers aunque no se mencione explícitamente
            has_superpowers = False
            for t in all_loaded_tools:
                if any(k in t.lower() for k in capabilities["superpowers"]):
                    has_superpowers = True
                    break
            if not has_superpowers:
                missing_tools.append("superpowers (flujos TDD/Subagent)")

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
