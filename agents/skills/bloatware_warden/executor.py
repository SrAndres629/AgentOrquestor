import os
import sys
from core.event_bus import bus

class BloatwareWarden:
    """
    Skill de Higiene Arquitectónica (Soberanía de Espacio).
    Asegura que el Bloatware resida en la Unidad D y el Núcleo permanezca limpio.
    """
    def __init__(self, bloatware_path="/home/jorand/Escritorio/Biblioteca MCP/superpowers/bloatware"):
        self.bloatware_path = bloatware_path
        self.forbidden_dirs = ["node_modules", "venv", "__pycache__", "datasets", "models"]

    async def enforce_hygiene(self, target_dir: str):
        sys.stderr.write(f"🧹 [WARDEN] Auditando higiene en: {target_dir}\n")
        
        found_bloat = []
        for root, dirs, files in os.walk(target_dir):
            for d in dirs:
                if d in self.forbidden_dirs:
                    found_bloat.append(os.path.join(root, d))
        
        if found_bloat:
            sys.stderr.write(f"⚠️ [WARDEN] Alerta de Bloatware detectada: {found_bloat}\n")
            sys.stderr.write(f"📢 [RECORDE] Agentes: El bloatware DEBE ir en la Unidad D. El Escritorio es solo para Lógica Core.\n")
            
            # Notificar al Event Bus para que el Meta_Engineer considere moverlo
            await bus.publish("BLOATWARE_DETECTED", data={"paths": found_bloat})
            return False
        
        sys.stderr.write("🟢 [WARDEN] Espacio de trabajo purificado. Solo archivos importantes detectados.\n")
        return True

executor = BloatwareWarden()
