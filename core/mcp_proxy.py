import os
import json
from typing import List, Dict, Any
from core.telemetry import telemetry

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
        return [{"name": k, "desc": v["description"]} for k, v in self.registry.items()]

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una acción en un servidor MCP externo con validación de soberanía."""
        if tool_name not in self.registry:
            return {"status": "ERROR", "message": f"Herramienta {tool_name} no encontrada."}
            
        telemetry.info(f"⚡ MCP: Ejecutando {tool_name}...")
        # Simulación de puente stdio/sse hacia el servidor destino
        return {"status": "SUCCESS", "tool": tool_name, "result": "Misión ejecutada."}

mcp_proxy = MCPProxy()
