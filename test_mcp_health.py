import asyncio
import json
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def test_server():
    print("[*] Iniciando Handshake MCP con AgentOrquestor...")
    # Corregimos la llamada al SDK
    server = StdioServerParameters(command=sys.executable, args=["-B", "main.py"])
    async with stdio_client(server) as (read, write):
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
            server_ok = False
            try:
                payload = json.loads(result.content[0].text)
                server_ok = payload.get("status") == "OK"
                print(json.dumps(payload, indent=2))
            except Exception:
                print(result.content[0].text)
            
            if server_ok:
                print("\n[Veredicto] AGENT_ORQUESTOR: 100% FUNCIONAL")
            else:
                print("\n[Veredicto] AGENT_ORQUESTOR: ERROR EN RESPUESTA")

if __name__ == "__main__":
    asyncio.run(test_server())
