import os
import json
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# --- Fase 1: Setup y Dependencias Base ---

# Configuración de rutas (Estandarización OSAA v6.0)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORTEX_DIR = PROJECT_ROOT / ".cortex"
BUS_LOG = CORTEX_DIR / "bus_buffer.jsonl"

app = FastAPI(title="OSAA War Room Server (Pillar 1)")

# Configuración CORS: Permitir acceso desde el frontend local (Vite/Chrome)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WarRoom")

# --- Fase 2: El Radar de Tmux (Hardware Awareness) ---

async def get_active_agents() -> List[Dict[str, str]]:
    """
    Escanea las sesiones de tmux para identificar agentes vivos.
    """
    try:
        # Ejecutar 'tmux ls' y capturar salida
        process = await asyncio.create_subprocess_exec(
            "tmux", "ls",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        
        if process.returncode != 0:
            return []

        sessions = []
        for line in stdout.decode().splitlines():
            if ":" in line:
                name = line.split(":")[0].strip()
                sessions.append({"session_name": name, "status": "ACTIVE"})
        return sessions
    except Exception as e:
        logger.error(f"Error detectando tmux: {e}")
        return []

# --- Fase 3: El Lector Asíncrono del Bus (File Tailing) ---

async def tail_cortex_bus():
    """
    Generador asíncrono que hace tailing de bus_buffer.jsonl.
    Solo emite nuevos registros desde el momento de la conexión.
    """
    if not BUS_LOG.exists():
        logger.warning(f"Bus log no encontrado en {BUS_LOG}. Esperando creación...")
        while not BUS_LOG.exists():
            await asyncio.sleep(1)

    with open(BUS_LOG, "r", encoding="utf-8") as f:
        # Ir al final del archivo para leer solo lo nuevo
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.5)  # Latencia de refresco del búnker
                continue
            
            try:
                event = json.loads(line)
                yield event
            except json.JSONDecodeError:
                continue

# --- Fase 4: El Enrutador WebSocket y Endpoints API ---

@app.get("/api/status")
async def get_status():
    """Estado general del bus y misiones."""
    bus_exists = BUS_LOG.exists()
    return {
        "status": "ONLINE",
        "bus_path": str(BUS_LOG),
        "bus_active": bus_exists,
        "timestamp": os.path.getmtime(BUS_LOG) if bus_exists else None
    }

@app.get("/api/tmux")
async def get_tmux():
    """Lista de agentes vivos en tmux."""
    return await get_active_agents()

@app.websocket("/ws/feed")
async def websocket_endpoint(websocket: WebSocket):
    """
    El Megáfono: Transmite eventos del bus y estado de agentes en tiempo real.
    """
    await websocket.accept()
    logger.info("📡 Cliente conectado al feed WebSocket.")
    
    # Cola de eventos para manejar concurrencia
    stop_event = asyncio.Event()

    async def broadcast_bus_events():
        async for event in tail_cortex_bus():
            if stop_event.is_set():
                break
            try:
                await websocket.send_json({"type": "BUS_EVENT", "data": event})
            except Exception:
                stop_event.set()
                break

    async def broadcast_agent_status():
        while not stop_event.is_set():
            try:
                agents = await get_active_agents()
                await websocket.send_json({"type": "TMUX_STATUS", "data": agents})
                await asyncio.sleep(2.0)  # Latencia del radar
            except Exception:
                stop_event.set()
                break

    # Ejecutar ambos monitores simultáneamente
    try:
        await asyncio.gather(
            broadcast_bus_events(),
            broadcast_agent_status()
        )
    except WebSocketDisconnect:
        logger.info("🔌 Cliente desconectado.")
    finally:
        stop_event.set()

if __name__ == "__main__":
    import uvicorn
    # Levantamos el megáfono en el puerto 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
