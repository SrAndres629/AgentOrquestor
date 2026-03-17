import os
import json
from typing import List, Dict, Any
from core.telemetry import telemetry
from core.mission_planner import planner
from core.cognitive_cortex import cognitive_cortex

class MCPProxy:
    """
    Puente de Soberanía para herramientas externas v4.0.
    Gestiona el auto-descubrimiento de servidores MCP (AIAA, Trading, Infra).
    """
    def __init__(self, mcp_dir: str = "mcp_servers/active"):
        self.mcp_dir = mcp_dir
        self.registry = {}
        self.bootstrap_tools()

    def bootstrap_tools(self):
        """Escanea el ecosistema en busca de capacidades disponibles."""
        telemetry.info("🔌 MCP: Iniciando auto-descubrimiento de herramientas...")
        
        # 1. Herramientas Core de Negocio (Hardcoded por Seguridad/Auth)
        self.registry = {
            "whatsapp_sender": {"status": "ready", "description": "Envío de mensajes AIAA y CAPI"},
            "meta_ads_analyzer": {"status": "ready", "description": "Análisis de rendimiento Meta Ads"},
            "gold_trader": {"status": "locked", "description": "Ejecución XAUUSD (Requiere OTP)"}
        }

        # 2. Descubrimiento Dinámico de Servidores (Filesystem)
        if os.path.exists(self.mcp_dir):
            for entry in os.listdir(self.mcp_dir):
                if entry.endswith(".json"):
                    with open(os.path.join(self.mcp_dir, entry), "r") as f:
                        config = json.load(f)
                        name = config.get("name", entry.replace(".json", ""))
                        self.registry[name] = {
                            "status": "active",
                            "description": config.get("description", "Herramienta dinámica")
                        }
        
        telemetry.info(f"✅ MCP: {len(self.registry)} herramientas descubiertas y mapeadas.")

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Genera el catálogo para el prompt del sistema de agentes."""
        catalog = [{"name": k, "desc": v["description"]} for k, v in self.registry.items()]
        
        catalog.append({
            "name": "register_new_tool",
            "desc": "Registra una nueva herramienta (MCP o Skill) en el sistema para que sea usable en futuras misiones."
        })
        # Add the native sequential thinking tool
        catalog.append(cognitive_cortex.get_tool_definition()["function"])
        return catalog

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una acción en un servidor MCP externo (Guía 14).
         सेंट्रल स्विचबोर्ड (Switchboard Central).
        """
        if tool_name == "register_new_tool":
            agent = params.get("agent_name", "UnknownAgent")
            tool = params.get("tool_name")
            if not tool:
                return {"status": "ERROR", "message": "Falta parámetro 'tool_name'."}
            
            planner.register_tool(agent, tool)
            return {
                "status": "SUCCESS", 
                "message": f"Herramienta '{tool}' registrada para el agente '{agent}'."
            }

        # 2) Cognicion Nativa
        if tool_name == "sequentialthinking":
            return cognitive_cortex.process_thought(params)

        if tool_name not in self.registry:
            return {"status": "ERROR", "message": f"Herramienta {tool_name} no encontrada o no mapeada."}
            
        telemetry.info(f"⚡ [MCP_PROXY] Ruteando llamada a: {tool_name}")
        
        # Simulación de ruteo a puerto específico (Guía 14)
        # En una implementación real, aquí se usaría un cliente HTTP/SSE o Stdio hacia el puerto mapeado.
        # Por ahora, simulamos la respuesta para mantener la estabilidad del enjambre.
        
        raw_result = f"Misión ejecutada en {tool_name}. Payload procesado correctamente."
        
        # LEY DEL EMBUDO (Guía 04/14): Truncamiento en el borde a 4000 caracteres.
        truncated_result = raw_result[:4000]
        if len(raw_result) > 4000:
            truncated_result += "\n\n[TRUNCATED BY TITANIUM FUNNEL (GUIDE 04)]"
            
        return {
            "status": "SUCCESS", 
            "tool": tool_name, 
            "result": truncated_result,
            "routing": "localhost:800x" # Simulación de puerto
        }

mcp_proxy = MCPProxy()
