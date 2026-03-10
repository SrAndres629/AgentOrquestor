import asyncio
import json
import sys
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

async def test_server():
    print("[*] Iniciando Handshake MCP con AgentOrquestor...")
    # Corregimos la llamada al SDK
    async with stdio_client(".venv/bin/python", ["main.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Inicialización
            await session.initialize()
            print("[+] Conexión establecida (JSON-RPC 2.0)")
            
            # 2. Listar herramientas
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"[+] Herramientas detectadas: {tool_names}")
            
            # 3. Prueba de Herramienta (Capa 0 - Router con API Cloud)
            # Esto verificará que tu llave de OpenRouter funciona para los embeddings
            print("[*] Probando Capa 0 (Semantic Router con OpenRouter)...")
            result = await session.call_tool("direct_refactor", {"intent": "test de integracion de red"})
            
            print("[+] RESULTADO DEL SERVIDOR:")
            print(json.dumps(json.loads(result.content[0].text), indent=2))
            
            if "SWARM_AWAKE" in result.content[0].text or "CACHE_HIT" in result.content[0].text:
                print("\n[Veredicto] AGENT_ORQUESTOR: 100% FUNCIONAL")
            else:
                print("\n[Veredicto] AGENT_ORQUESTOR: ERROR EN RESPUESTA")

if __name__ == "__main__":
    asyncio.run(test_server())
