import os
import json
import asyncio
from typing import Dict, Any, List
from core.hardware_monitor import HardwareMonitor
from core.mission_planner import MissionPlanner
from core.telemetry import telemetry

hardware_monitor = HardwareMonitor()

class Bootstrapper:
    def __init__(self):
        self.planner = MissionPlanner()

    async def plan_mission(self, raw_order: str) -> Dict[str, Any]:
        hw_stats = hardware_monitor.check_stability()
        vram_available = hw_stats['vram']['vram_total'] - hw_stats['vram']['vram_used']
        telemetry.info(f'Análisis metabólico: {vram_available}MB VRAM detectados.')
        if vram_available > 3500:
            agent_config = ['LeadDev', 'SecurityQA']
            mode = 'DIALECTIC'
        else:
            agent_config = ['Architect']
            mode = 'EFFICIENCY'
        tasks = ['Escaneo de dependencias', 'Análisis de hardware', 'Optimización']
        manifest = self.planner.create_manifest(user_order=raw_order, tasks=tasks)
        manifest_data = manifest.model_dump()
        manifest_data['mode'] = mode
        manifest_data['agents'] = agent_config
        return manifest_data

    async def ignite_swarm(self, manifest: Dict[str, Any]):
        mission_id = manifest['mission_id']
        mode = manifest['mode']
        telemetry.info(f'Ignición Swarm {mission_id} en modo {mode}')
        mission_path = f'.cortex/missions/{mission_id}'
        os.makedirs(mission_path, exist_ok=True)
        with open(f'{mission_path}/manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        for agent in manifest['agents']:
            telemetry.info(f'Terminal {agent} activada.')
            await asyncio.sleep(0.5)
        print(f'Swarm desplegado en: {mission_path}')

bootstrapper = Bootstrapper()
