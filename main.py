import sys
import os
import json
import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

server = Server('agentOrquestor-v5-final')

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(name='ignite_mission', description='Inicia misión real.', inputSchema={'type': 'object', 'properties': {'goal': {'type': 'string'}}, 'required': ['goal']}),
        types.Tool(name='semantic_audit', description='Auditoría real.', inputSchema={'type': 'object'}),
        types.Tool(name='launch_swarm', description='Lanzar enjambre real.', inputSchema={'type': 'object', 'properties': {'goal': {'type': 'string'}, 'mode': {'type': 'string', 'enum': ['DIALECTIC', 'EFFICIENCY', 'FULL_SWARM']}}, 'required': ['goal']}),
        types.Tool(name='evaluate_handoff', description='Evaluar handoff real.', inputSchema={'type': 'object', 'properties': {'mission_id': {'type': 'string'}, 'iteration': {'type': 'integer'}}, 'required': ['mission_id']}),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}
    if name == 'ignite_mission':
        from ignite import execute_mission
        res = await execute_mission(arguments.get('goal', ''))
        return [types.TextContent(type='text', text=json.dumps(res, default=str))]
    elif name == 'semantic_audit':
        from core.hardware_monitor import HardwareMonitor
        res = HardwareMonitor().check_stability()
        return [types.TextContent(type='text', text=json.dumps(res, default=str))]
    elif name == 'launch_swarm':
        from core.swarm_launcher import SwarmLauncher
        res = await SwarmLauncher().launch(arguments.get('goal', ''), arguments.get('mode', 'DIALECTIC'))
        return [types.TextContent(type='text', text=json.dumps(res, default=str))]
    elif name == 'evaluate_handoff':
        from core.handoff_router import handoff_router
        res = handoff_router.evaluate_and_route(arguments.get('mission_id', ''), iteration=arguments.get('iteration', 0))
        return [types.TextContent(type='text', text=json.dumps(res, default=str))]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, InitializationOptions(server_name='agentOrquestor', server_version='5.0', capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}))) 

if __name__ == '__main__':
    asyncio.run(main())
