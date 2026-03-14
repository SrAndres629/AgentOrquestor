import sys
import os
import json
import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Mandato de Soberanía para Inyección en Herramientas
SOVEREIGNTY_PREFIX = "[OSAA v5.0] REGLA: Requiere Handshake Dialéctico. "

server = Server('agentOrquestor-unificado-v5')

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name='ignite_mission', 
            description=f'{SOVEREIGNTY_PREFIX}Inicializa una misión bajo el protocolo de soberanía cognitiva y telemetría de hardware.',
            inputSchema={
                'type': 'object',
                'properties': {
                    'goal': {'type': 'string', 'description': 'Objetivo de la misión'}
                },
                'required': ['goal']
            }
        ),
        types.Tool(
            name='semantic_audit', 
            description=f'{SOVEREIGNTY_PREFIX}Auditoría profunda de archivos core para identificar ineficiencias de VRAM.',
            inputSchema={'type': 'object'}
        ),
        types.Tool(
            name='launch_swarm',
            description=f'{SOVEREIGNTY_PREFIX}Despliega el enjambre distribuido en terminales tmux aisladas con IPC atómico.',
            inputSchema={
                'type': 'object',
                'properties': {
                    'goal': {'type': 'string', 'description': 'Objetivo de la misión'},
                    'mode': {
                        'type': 'string',
                        'description': 'Modo del enjambre: DIALECTIC | EFFICIENCY | FULL_SWARM',
                        'enum': ['DIALECTIC', 'EFFICIENCY', 'FULL_SWARM'],
                        'default': 'DIALECTIC'
                    }
                },
                'required': ['goal']
            }
        ),
        types.Tool(
            name='evaluate_handoff',
            description=f'{SOVEREIGNTY_PREFIX}Evalúa el estado del debate y enruta: SEAL (consenso) o HANDOFF (re-iteración).',
            inputSchema={
                'type': 'object',
                'properties': {
                    'mission_id': {'type': 'string', 'description': 'ID de la misión activa'},
                    'iteration': {'type': 'integer', 'description': 'Número de iteración actual', 'default': 0}
                },
                'required': ['mission_id']
            }
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}

    if name == 'launch_swarm':
        from core.swarm_launcher import SwarmLauncher
        launcher = SwarmLauncher()
        goal = arguments.get('goal', 'Misión por defecto')
        mode = arguments.get('mode', 'DIALECTIC')
        result = await launcher.launch(goal, mode)
        return [types.TextContent(type='text', text=json.dumps(result, ensure_ascii=False, default=str))]

    elif name == 'evaluate_handoff':
        from core.handoff_router import handoff_router
        mission_id = arguments.get('mission_id', '')
        iteration = arguments.get('iteration', 0)
        result = handoff_router.evaluate_and_route(mission_id, iteration=iteration)
        return [types.TextContent(type='text', text=json.dumps(result, ensure_ascii=False, default=str))]

    # Default handler para herramientas existentes (ignite_mission, semantic_audit)
    return [types.TextContent(type='text', text=json.dumps({'status': 'OK', 'msg': 'Handshake Cognitivo Iniciado'}))]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name='agentOrquestor', server_version='5.0-Sovereign',
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == '__main__':
    asyncio.run(main())
