import os
import fcntl
import sys

class PersistenceManager:
    def __init__(self, db_path='/home/jorand/Escritorio/Biblioteca MCP/AgentOrquestor/memory/graph/persistence.db'):
        self.db_path = db_path
        self.lock_file = db_path + '.lock'

    def acquire_db_lock(self, task_id: str | None = None):
        """
        Bloqueo atómico para acceso a DB.
        Soporta sharding del lock por task_id para reducir contención bajo swarm.
        """
        lock_path = self.lock_file
        if task_id:
            lock_path = f"{self.db_path}.{task_id}.lock"
        f = open(lock_path, 'w')
        try:
            fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except IOError:
            sys.stderr.write("⚠️ [PERSISTENCE] Acceso denegado: Otro agente está escribiendo en la Unidad D.\n")
            return None

persistence = PersistenceManager()
