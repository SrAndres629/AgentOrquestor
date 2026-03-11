import sys
import json
import asyncio
from core.bootstrapper import bootstrapper

async def ignite():
    print('🚀 [IGNITE] Iniciando OSAA v4.0 - Modo Soberanía')
    order = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Misión General'
    
    manifest = await bootstrapper.plan_mission(order)
    await bootstrapper.ignite_swarm(manifest)

if __name__ == '__main__':
    asyncio.run(ignite())
