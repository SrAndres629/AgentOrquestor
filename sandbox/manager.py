import subprocess
import os
import shutil
import tempfile
import time
from typing import Dict, Any
from core.telemetry import telemetry

class SandboxManager:
    """
    Entorno de Ejecución Seguro v4.0.
    Valida las soluciones del enjambre antes del despliegue final.
    """
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.workspace_base = ".cortex/sandbox"
        os.makedirs(self.workspace_base, exist_ok=True)

    def run_validation(self, code_snippet: str, filename: str = "test_run.py") -> Dict[str, Any]:
        """
        Ejecuta código en un directorio temporal aislado.
        """
        temp_dir = tempfile.mkdtemp(dir=self.workspace_base)
        file_path = os.path.join(temp_dir, filename)
        
        telemetry.info(f"🛡️ Sandbox: Iniciando validación en {temp_dir}")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_snippet)

        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["python3", file_path],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            status = "SUCCESS" if result.returncode == 0 else "FAILED"
            
            output = {
                "status": status,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "execution_time": round(execution_time, 3)
            }
            
            telemetry.emit_event("SANDBOX_EXECUTION_COMPLETE", output)
            return output

        except subprocess.TimeoutExpired:
            telemetry.error(f"❌ Sandbox: Timeout de {self.timeout}s alcanzado.")
            return {"status": "TIMEOUT", "stderr": "Execution exceeded time limit."}
        except Exception as e:
            telemetry.error(f"❌ Sandbox: Error crítico: {e}")
            return {"status": "CRITICAL_ERROR", "stderr": str(e)}

sandbox_manager = SandboxManager()
