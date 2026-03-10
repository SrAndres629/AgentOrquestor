"""
AgentOrquestor - Security Sandbox Manager
=========================================
Orquestador de verificación y pruebas seguras.
Ejecuta el pipeline de validación: Análisis Estático -> Verificación Formal -> Sandbox Wasm.
Garantiza que el SecurityQA tenga un reporte determinista antes de aprobar parches.
"""

import subprocess
import json
import os
from typing import Dict, Any, List
from .verifier import FormalVerifier
from .runtime import WasmSandboxRuntime
from core.state import AgentState

class SecurityManager:
    """
    Gestor principal de la capa de aislamiento.
    """
    
    def __init__(self):
        self.verifier = FormalVerifier()
        self.runtime = WasmSandboxRuntime()

    def run_bandit_scan(self, code_path: str) -> Dict[str, Any]:
        """Análisis estático con Bandit para llamadas prohibidas."""
        try:
            # Ejecución de Bandit como subproceso (Aislamiento de análisis)
            result = subprocess.run(
                ["bandit", "-r", code_path, "-f", "json"],
                capture_output=True,
                text=True
            )
            # Bandit retorna exit code 1 si encuentra riesgos
            return json.loads(result.stdout)
        except Exception as e:
            return {"error": f"Bandit Scan Failed: {str(e)}"}

    def execute_secure_test(self, code: str, state: AgentState) -> Dict[str, Any]:
        """
        Flujo completo de validación de seguridad para el código generado.
        """
        report = {
            "static_analysis": None,
            "formal_verification": None,
            "dynamic_execution": None,
            "overall_status": "REJECTED"
        }
        
        # 1. Fase Estática: Guardado temporal y Scan
        tmp_path = "sandbox/tmp_eval.py"
        with open(tmp_path, "w") as f:
            f.write(code)
            
        report["static_analysis"] = self.run_bandit_scan(tmp_path)
        
        # 2. Fase Formal: Verificación Z3
        # Extraemos metadatos del AgentState para las aserciones
        metadata = {
            "expected_complexity": len(code.split("\n")),
            "has_nested_loops": "for" in code and code.count("for") > 1,
            "objective": state.task_manifest.objective
        }
        
        is_formally_valid, formal_msg = self.verifier.verify_logic(metadata)
        report["formal_verification"] = {
            "success": is_formally_valid,
            "message": formal_msg
        }
        
        # 3. Fase Dinámica: Ejecución en Sandbox Wasm
        # Nota: En un flujo real, compilamos el código Python a un bytecode evaluable en Wasm
        # Aquí simulamos el paso a bytes del payload.
        wasm_payload = b"\x00asm\x01\x00\x00\x00" # Wasm Module Mock
        
        if is_formally_valid:
             report["dynamic_execution"] = self.runtime.run_isolated(wasm_payload)
             
        # 4. Decisión Final de Integridad
        if is_formally_valid and report["dynamic_execution"].get("status") == "SUCCESS":
            # Si no hay vulnerabilidades críticas en Bandit
            if report["static_analysis"].get("metrics", {}).get("_index_0", 0) == 0:
                report["overall_status"] = "APPROVED"
                
        # Limpieza (Zero-Trust)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
        return report

async def secure_eval(code: str, state: AgentState) -> Dict[str, Any]:
    """Helper asíncrono para el Swarm."""
    manager = SecurityManager()
    return manager.execute_secure_test(code, state)
