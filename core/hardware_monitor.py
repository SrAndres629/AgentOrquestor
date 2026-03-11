import os
import psutil
import subprocess
import json
import time
from typing import Dict, Any

class HardwareMonitor:
    """
    Sentinel de Telemetría v4.0.
    Monitorea VRAM, RAM, CPU y Térmicos en tiempo real para el OSAA.
    """
    def __init__(self, vram_limit_mb: int = 5800):
        self.vram_limit = vram_limit_mb
        self.critical_temp = 85.0

    def get_vram_usage(self) -> Dict[str, float]:
        """Obtiene el uso de VRAM mediante nvidia-smi."""
        try:
            # Comando optimizado para Linux / Asus M16
            cmd = "nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd.split(), stderr=subprocess.DEVNULL).decode('utf-8').strip().split(',')
            used, total, temp = [float(x) for x in output]
            return {"vram_used": used, "vram_total": total, "gpu_temp": temp}
        except Exception:
            return {"vram_used": 0.0, "vram_total": 0.0, "gpu_temp": 0.0}

    def get_system_stats(self) -> Dict[str, float]:
        """Telemetría de CPU y RAM."""
        ram = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_percent": ram.percent
        }

    def check_stability(self) -> Dict[str, Any]:
        """Evalúa si el hardware es estable para una misión de alta intensidad."""
        vram = self.get_vram_usage()
        sys = self.get_system_stats()
        
        is_safe = (vram["vram_used"] < self.vram_limit) and (vram["gpu_temp"] < self.critical_temp)
        
        return {
            "timestamp": time.time(),
            "status": "STABLE" if is_safe else "CRITICAL",
            "vram": vram,
            "system": sys,
            "action": "PROCEED" if is_safe else "THROTTLE"
        }

if __name__ == "__main__":
    monitor = HardwareMonitor()
    print(json.dumps(monitor.check_stability(), indent=2))
