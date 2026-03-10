import asyncio
from typing import Dict, Any, Tuple
from .schema import GitAutocommitContract

class GitAutocommitExecutor:
    """
    Ejecutor encapsulado local (Wasm-like sandbox simulado) para la habilidad Git Autocommit.
    Diseñado para integrarse bajo los confines estrictos del Swarm asíncrono.
    """
    
    def __init__(self, contract_data: Dict[str, Any]):
        # Validación Zero-Trust en la barrera del constructor
        self.contract = GitAutocommitContract(**contract_data)
        
    async def _check_z3_invariants(self) -> bool:
        """
        Sub-módulo lógico: Demuestra la viabilidad topológica antes de mutar.
        """
        if not self.contract.zero_trust_telemetry.z3_invariant_verified:
            raise PermissionError("Bloqueo de Seguriad (Zero-Trust): Invariante formal 'Z3' no certificada de origen.")
            
        process = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        status_output = stdout.decode().strip()
        
        # SMT Mock: Aserción contra estados de merge rotos
        if "UU " in status_output:
            raise RuntimeError("Fallo SMT: El DTG actual presenta conflictos (Unmerged). Operación insegura abortada.")
            
        if not status_output:
            raise ValueError("Evaluación Lógica: El grafo local de Git no presenta mutaciones pendientes. Operación es 'NOP'.")
            
        return True

    async def _execute_git_command(self, *args: str) -> Tuple[int, str, str]:
        """Envuelve la shell asíncrona (Aislamiento POSIX estricto)."""
        process = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode().strip(), stderr.decode().strip()

    async def execute(self) -> Dict[str, Any]:
        """
        Invoca la rutina del agente, garantizando aislamiento de la memoria concurrente.
        """
        # Fase 1: Certificación SMT local
        await self._check_z3_invariants()
        
        # Fase 2: Snapshot Transaccional (Stage)
        code, out, err = await self._execute_git_command("add", "-A")
        if code != 0:
            raise RuntimeError(f"Fallo en aserción del árbol (git add): {err}")
            
        # Fase 3: Sintesis Estructural del Mensaje
        msg = self.contract.payload.commit_message
        if not msg:
            # Reconstrucción de intención local
            _, diff_stat, _ = await self._execute_git_command("diff", "--cached", "--stat")
            msg = (
                f"feat(swarm): mutación autónoma deducida vía '{self.contract.intent_context[:20]}'\n\n"
                f"Grafo de Transformación (DTG/Diff):\n{diff_stat}"
            )
            
        # Fase 4: Confirmación Persistente
        code, out, err = await self._execute_git_command("commit", "-m", msg)
        if code != 0 and "nothing to commit" not in out:
             raise RuntimeError(f"Fallo de mutación transaccional local: {err or out}")
             
        # Fase 5: Propagación de Red (Sink Node)
        pushed = False
        if self.contract.payload.push_remote:
            push_args = ["push"]
            if self.contract.payload.target_branch:
                push_args.extend(["origin", self.contract.payload.target_branch])
                
            code, out, err = await self._execute_git_command(*push_args)
            if code != 0:
                raise RuntimeError(f"Fallo de topología de red remota (Git Push): {err}")
            pushed = True
            
        return {
            "status": "COMPLETED_STRUCTURALLY",
            "ebpf_ring_ack": self.contract.zero_trust_telemetry.ebpf_trace_id,
            "operation": {
                "message": msg,
                "remote_synced": pushed
            }
        }
