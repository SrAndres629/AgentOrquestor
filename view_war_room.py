import os
import json
import glob
from ui.war_room import WarRoom

def get_latest_mission():
    """Busca la misión más reciente en la bóveda .cortex del usuario."""
    missions_dir = '/home/jorand/.cortex/missions'
    missions = glob.glob(os.path.join(missions_dir, '*'))
    if not missions:
        return None
    latest_mission = max(missions, key=os.path.getmtime)
    return os.path.basename(latest_mission)

def state_callback():
    mission_id = get_latest_mission()
    if not mission_id:
        return {}
    path = f'/home/jorand/.cortex/missions/{mission_id}/manifest.json'
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

if __name__ == '__main__':
    mission_id = get_latest_mission()
    if mission_id:
        print(f'🛰️ Conectando a la misión: {mission_id}')
        wr = WarRoom(mission_id)
        wr.run(state_callback)
    else:
        print('❌ No se detectaron misiones activas en /home/jorand/.cortex/missions/')
