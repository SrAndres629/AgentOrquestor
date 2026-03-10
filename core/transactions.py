"""
AgentOrquestor - Transactional Management (Git Safety)
======================================================
Garantiza la integridad del repositorio. 
Crea ramas aisladas antes de cada sesión (Atomic Sessions) y permite 
Rollbacks instantáneos (git reset --hard) si el Sandbox de seguridad falla.
"""

from git import Repo, exc
import uuid
import os

class TransactionManager:
    """
    Gestor de seguridad transaccional basado en Git.
    """
    def __init__(self, repo_path: str = "."):
        self.repo = Repo(repo_path)
        self.main_branch = self.repo.active_branch.name
        self.current_session_branch = None

    def start_atomic_session(self) -> str:
        """Crea un checkout a una rama temporal de agente."""
        session_id = f"agent_session_{uuid.uuid4().hex[:8]}"
        try:
            # Crear y cambiar a la rama de sesión
            new_branch = self.repo.create_head(session_id)
            new_branch.checkout()
            self.current_session_branch = session_id
            return session_id
        except Exception as e:
            raise RuntimeError(f"Fallo al iniciar sesión transaccional: {str(e)}")

    def rollback_session(self):
        """Si el Sandbox falla, deshacemos todo y volvemos a main."""
        if not self.current_session_branch: return
        
        # Limpieza forzada y vuelta a main
        self.repo.git.reset('--hard')
        self.repo.git.checkout(self.main_branch)
        # Opcional: Borrar rama de error
        # self.repo.delete_head(self.current_session_branch, force=True)
        self.current_session_branch = None

    def commit_and_merge(self, message: str):
        """Confirma los cambios y los fusiona en la rama principal tras aprobación."""
        if not self.current_session_branch: return
        
        self.repo.git.add(A=True)
        self.repo.index.commit(message)
        
        # Merge de vuelta a la rama principal (E.g. master/main)
        self.repo.git.checkout(self.main_branch)
        self.repo.git.merge(self.current_session_branch)
        self.current_session_branch = None

# Singleton de transacciones
git_guard = TransactionManager()
