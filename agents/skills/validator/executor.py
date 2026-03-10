import os
import subprocess
import sys
from core.event_bus import bus

class PostTaskValidator:
    """
    Skill de Autodiagnóstico (Fase 5).
    Verifica la integridad del sistema tras cada cambio estructural.
    """
    async def validate_system(self, file_paths: list):
        print("🔍 [VALIDATOR] Iniciando autodiagnóstico de integridad...")
        
        errors = []
        for file in file_paths:
            if file.endswith(".py") and os.path.exists(file):
                # 1. Chequeo de Sintaxis
                result = subprocess.run(["python3", "-m", "py_compile", file], capture_output=True)
                if result.returncode != 0:
                    errors.append(f"Syntax error in {file}: {result.stderr.decode()}")
        
        # 2. Chequeo de Importación del Core
        try:
            from core.telemetry import telemetry
            from core.event_bus import bus as event_bus
            print("✅ [VALIDATOR] Core operacional (Imports OK)")
        except Exception as e:
            errors.append(f"Core breakdown: {str(e)}")
            
        if not errors:
            print("🎊 [VALIDATOR] Sistema íntegro. Cambio verificado con éxito.")
            await bus.publish("SYSTEM_VALIDATED", data={"status": "CLEAN"})
            return True
        else:
            print(f"❌ [VALIDATOR] Fallos detectados: {errors}")
            await bus.publish("SYSTEM_VALIDATION_FAILED", data={"errors": errors})
            return False

executor = PostTaskValidator()
