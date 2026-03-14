import os
import fcntl
import sys

class PersistenceManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Redirigir a .cortex según OSAA v6.0
            base_dir = Path(__file__).resolve().parent.parent
            self.db_path = str(base_dir / ".cortex" / "persistence.db")
        else:
            self.db_path = db_path
        self.lock_file = self.db_path + '.lock'
        # Asegurar que el directorio exista
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

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
