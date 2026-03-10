import os
import subprocess
import sys
from core.event_bus import bus
from core.telemetry import telemetry

class PostTaskValidator:
    """
    Skill de Autodiagnóstico (Fase 5).
    Verifica la integridad del sistema tras cada cambio estructural.
    """
    async def validate_system(self, file_paths: list):
        telemetry.info("🔍 [VALIDATOR] Iniciando autodiagnóstico de integridad...")
        
        errors = []
        for file in file_paths:
            if file.endswith(".py") and os.path.exists(file):
                # 1. Chequeo de Sintaxis
                env = dict(os.environ)
                env["PYTHONPYCACHEPREFIX"] = "/tmp/pycache"
                result = subprocess.run(["python3", "-B", "-m", "py_compile", file], capture_output=True, env=env, text=True)
                if result.returncode != 0:
                    errors.append(f"Syntax error in {file}: {result.stderr}")
        
        # 2. Chequeo de Importación del Core
        try:
            from core.telemetry import telemetry
            from core.event_bus import bus as event_bus
            telemetry.info("✅ [VALIDATOR] Core operacional (Imports OK)")
        except Exception as e:
            errors.append(f"Core breakdown: {str(e)}")
            
        if not errors:
            telemetry.info("🎊 [VALIDATOR] Sistema íntegro. Cambio verificado con éxito.")
            await bus.publish("SYSTEM_VALIDATED", data={"status": "CLEAN"})
            return True
        else:
            telemetry.error(f"❌ [VALIDATOR] Fallos detectados: {errors}")
            await bus.publish("SYSTEM_VALIDATION_FAILED", data={"errors": errors})
            return False

executor = PostTaskValidator()
