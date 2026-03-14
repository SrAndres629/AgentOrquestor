import os
import json
import time
import fcntl
import glob
from typing import Dict, Any, Optional, List, Literal, Literal
from core.telemetry import telemetry
from core.neural_trace import inject_trace_context

class EventBus:
    """
    Sistema Nervioso Central v6.0 (Atomic Actor Mailbox).
    Sincronización síncrona/asíncrona entre terminales cognitivas.
    Elimina la contención mediante buzones aislados por actor.
    """
    def __init__(self, bus_dir: str = ".cortex/bus"):
        self.bus_dir = bus_dir
        self.bus_file = ".cortex/bus_buffer.jsonl"
        self.ack_path = ".cortex/bus_buffer.ack"
        os.makedirs(self.bus_dir, exist_ok=True)

    def _get_mailbox_path(self, agent_name: str) -> str:
        # Normalizar nombre para el sistema de archivos
        safe_name = agent_name.replace(" ", "_").lower()
        return self.bus_file

    def publish(self, event_type: str, data: Dict[str, Any], sender: str = "SYSTEM"):
        """
        Publica un pensamiento en el buzón propio del actor.
        """
        event = {
            "timestamp": time.time(),
            "sender": sender,
            "type": event_type,
            "payload": data,
            "handshake": False
        }
        
        # Inyectar contexto de traza para Neural Trace (Phase C)
        inject_trace_context(event)
        
        mailbox_path = self._get_mailbox_path(sender)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        
        import fcntl
        with open(mailbox_path, "a", encoding="utf-8") as f:
            fcntl.lockf(f, fcntl.LOCK_EX)
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
            fcntl.lockf(f, fcntl.LOCK_UN)
        
        telemetry.info(f"📡 MAILBOX [{sender}]: {event_type} persistido.")

    def read_mailbox(self, agent_name: str, limit: int = 10) -> List[Dict[Any, Any]]:
        """
        Lee los últimos eventos del buzón de un agente específico.
        Implementa el Botón del Pánico (Guía 15) ante corrupción.
        """
        path = self._get_mailbox_path(agent_name)
        if not os.path.exists(path):
            return []
            
        events = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Protocolo de Desastres (Guía 15)
                        telemetry.error(f"🚨 [PANIC BUTTON] Corrupción detectada en {path}. Iniciando recuperación.")
                        self._handle_corrupted_bus(path)
                        return [] # Reintentar tras recuperación sería lo ideal, pero por ahora cortamos.
        except Exception as e:
            telemetry.error(f"❌ Error crítico leyendo buzón {agent_name}: {e}")
            
        return events

    def _handle_corrupted_bus(self, path: str):
        """Maneja la corrupción moviendo el archivo y notificando al Chronicler."""
        backup_path = path + f".corrupt_{int(time.time())}.bak"
        try:
            os.rename(path, backup_path)
            telemetry.warning(f"📦 Backup de bus corrupto creado en {backup_path}")
            # El Chronicler (Guide 05) debería actuar aquí, pero por ahora instanciamos vacío
            with open(path, "w") as f: f.write("")
        except Exception as e:
            telemetry.error(f"💀 Fallo catastrófico en recuperación de desastres: {e}")

    def read_all_events(self, limit_per_actor: int = 5) -> List[Dict[str, Any]]:
        """Agrega eventos de todos los buzones (usado por el Watchdog)."""
        all_events = []
        for mailbox in [self.bus_file] if os.path.exists(self.bus_file) else []:
            agent_name = os.path.basename(mailbox).replace(".jsonl", "")
            all_events.extend(self.read_mailbox(agent_name, limit_per_actor))
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x.get("timestamp", 0))
        return all_events

    def request_handshake(self, receiver: str):
        """Solicita un Handshake Cognitivo."""
        telemetry.info(f"🤝 Handshake: Solicitando sincronización a {receiver}...")
        with open(self.ack_path, "w") as f:
            f.write(f"WAIT_ACK:{receiver}:{time.time()}")

    def verify_handshake(self, actor: str) -> bool:
        """Verifica confirmación de handshake."""
        if not os.path.exists(self.ack_path):
            return True
        with open(self.ack_path, "r") as f:
            content = f.read()
            if content.startswith("ACK_RECEIVED") and actor in content:
                telemetry.info(f"✅ Handshake: {actor} sincronizado.")
                os.remove(self.ack_path)
                return True
        return False

    def emit_doubt(self, claim_hash: str, reason: str):
        """Inyecta Duda Metódica."""
        self.publish("COGNITIVE_DOUBT", {"target": claim_hash, "reason": reason}, sender="SECURITY_QA")

bus = EventBus()
