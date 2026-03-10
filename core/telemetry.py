import asyncio
import os
from core.event_bus import bus

class LogSentinel:
    """Vigila los logs buscando patrones de error y fallos de ejecución."""
    def __init__(self, log_path="docs/telemetry.log"):
        self.log_path = log_path
        self.last_pos = 0

    async def watch(self):
        print(f"[SENTINEL] Iniciando vigilancia activa en {self.log_path}")
        # Aseguramos que el directorio docs existe
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                f.write("")

        while True:
            try:
                if os.path.exists(self.log_path):
                    with open(self.log_path, "r") as f:
                        f.seek(self.last_pos)
                        lines = f.readlines()
                        self.last_pos = f.tell()

                        for line in lines:
                            if "ERROR" in line or "Traceback" in line:
                                # Notificamos al enjambre que algo se rompió
                                await bus.publish("SYSTEM_ERROR_DETECTED", data={"error": line})
            except Exception as e:
                print(f"[SENTINEL] Error crítico en vigilancia: {e}")
            
            await asyncio.sleep(1) # Eficiencia de CPU para el i9
