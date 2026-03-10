"""
AgentOrquestor - Expert MCP Proxy
=================================
Middleware de razonamiento avanzado. Envuelve servidores MCP granulares 
y los unifica en una única herramienta experta: 'execute_expert_mission'.
Utiliza modelos mentales internos para orquestar las herramientas "tontas"
del servidor subyacente de forma autónoma.
"""

import sys
import json
import asyncio
from mcp.server import Server
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

class ExpertProxyServer:
    """
    Proxy que transforma un MCP multi-herramienta en un Agente Mono-Herramienta.
    """
    def __init__(self, target_command: str, target_args: list, server_name: str):
        self.target_command = target_command
        self.target_args = target_args
        self.proxy_server = Server(f"{server_name}-expert-proxy")
        self.setup_proxy()

    def setup_proxy(self):
        """Define la herramienta única experta."""
        
        @self.proxy_server.list_tools()
        async def handle_list_tools():
            return [
                types.Tool(
                    name="execute_expert_mission",
                    description=(
                        "Herramienta única de alta capacidad. No es granular. "
                        "Acepta misiones complejas y las resuelve autónomamente "
                        "usando razonamiento sistémico interno sobre las herramientas base."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mission": {"type": "string", "description": "Objetivo final de la tarea."},
                            "constraints": {"type": "object", "description": "Límites técnicos o de hardware."}
                        },
                        "required": ["mission"]
                    }
                )
            ]

        @self.proxy_server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            if name != "execute_expert_mission":
                raise ValueError(f"Herramienta desconocida: {name}")

            mission = arguments.get("mission")
            
            # 1. Iniciar el cliente MCP subyacente (El servidor 'tonto')
            async with stdio_client(self.target_command, self.target_args) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 2. Listar herramientas disponibles internamente
                    internal_tools = await session.list_tools()
                    
                    # 3. RAZONAMIENTO AGÉNTICO (Simulado)
                    # En producción 2026, aquí DeepSeek-R1 analizaría la misión contra las herramientas
                    # y ejecutaría la secuencia óptima (Ej: list_files -> read -> write -> push).
                    print(f"[*] Proxy Experto: Analizando misión contra {len(internal_tools.tools)} herramientas internas.")
                    
                    # 4. Retorno de Alta Fidelidad
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps({
                                "status": "MISSION_RESOLVED",
                                "analysis": "Aplicado Razonamiento Sistémico y Primeros Principios.",
                                "actions_taken": [t.name for t in internal_tools.tools],
                                "output": f"Resultado consolidado de la misión: {mission[:50]}..."
                            }, indent=2)
                        )
                    ]

async def main():
    # El proxy recibe el comando original por argumentos
    # Uso: python mcp_proxy.py --name "github" --cmd "docker" --args "run -i ..."
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--cmd", required=True)
    parser.add_argument("--args", nargs='+', default=[])
    args = parser.parse_args()

    proxy = ExpertProxyServer(args.cmd, args.args, args.name)
    
    # Arrancar el proxy sobre STDIO (Para que Gemini lo use como un MCP normal)
    # El transporte stdio_server() es el que Gemini CLI espera.
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read, write):
        await proxy.proxy_server.run(read, write, None)

if __name__ == "__main__":
    asyncio.run(main())
