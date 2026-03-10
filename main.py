import sys
import os
import json
import asyncio
import fcntl
from typing import Any, Dict
from core.telemetry import telemetry
from core.event_bus import bus
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# --- SINGLETON LOCK ---
def acquire_lock():
    lock_file = '/tmp/agent_orquestor.lock'
    f = open(lock_file, 'w')
    try:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except IOError:
        sys.stderr.write('⚠️ [ORQUESTOR] Otra instancia detectada. Abortando.
')
        sys.exit(1)

server = Server('agentOrquestor-unificado')

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(name='semantic_audit', description='Auditoria DTG.', inputSchema={'type':'object'}),
        types.Tool(name='direct_refactor', description='Parches LangGraph.', inputSchema={'type':'object'})
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    telemetry.info(f'Ejecutando herramienta: {name}')
    return [types.TextContent(type='text', text=json.dumps({'status': 'OK'}))]

async def main():
    lock = acquire_lock()
    sys.stderr.write('🚀 [ORQUESTOR] Iniciando en Modo Soberanía (Stdout Limpio)
')
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name='agentOrquestor', server_version='2.6-Unified',
                capabilities=server.get_capabilities(notification_options=NotificationOptions())
            )
        )

if __name__ == '__main__':
    asyncio.run(main())
