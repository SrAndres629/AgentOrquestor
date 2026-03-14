import os
import json
import time
import fcntl
from typing import Dict, Any, Optional
from core.telemetry import telemetry

class EventBus:
    """
    Sistema Nervioso Central v5.0.
    Sincronización síncrona/asíncrona entre terminales cognitivas.
    Multi-process safe: usa fcntl.LOCK_EX para escrituras atómicas.
    """
    def __init__(self, bus_path: str = ".cortex/bus_buffer.jsonl"):
        self.bus_path = bus_path
        self.ack_path = ".cortex/bus_buffer.ack"
        os.makedirs(os.path.dirname(self.bus_path), exist_ok=True)

    def publish(self, event_type: str, data: Dict[str, Any], sender: str = "SYSTEM"):
        """
        Publica un pensamiento o acción en el buffer compartido.
        Usa bloqueo exclusivo (fcntl.LOCK_EX) + fsync para garantizar
        que múltiples procesos no intercalen bytes en el JSONL.
        """
        event = {
            "timestamp": time.time(),
            "sender": sender,
            "type": event_type,
            "payload": data,
            "handshake": False
        }
        
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(self.bus_path, "a", encoding="utf-8") as f:
            fcntl.lockf(f, fcntl.LOCK_EX)
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
            fcntl.lockf(f, fcntl.LOCK_UN)
        
        telemetry.info(f"📡 BUS [{sender}]: {event_type} sincronizado.")

    def request_handshake(self, receiver: str):
        """Solicita un Handshake Cognitivo para asegurar alineación."""
        telemetry.info(f"🤝 Handshake: Solicitando sincronización a {receiver}...")
        with open(self.ack_path, "w") as f:
            f.write(f"WAIT_ACK:{receiver}:{time.time()}")

    def verify_handshake(self, actor: str) -> bool:
        """Verifica si la terminal opuesta ha confirmado el handshake."""
        if not os.path.exists(self.ack_path):
            return True
            
        with open(self.ack_path, "r") as f:
            content = f.read()
            if content.startswith("ACK_RECEIVED") and actor in content:
                telemetry.info(f"✅ Handshake: {actor} sincronizado correctamente.")
                os.remove(self.ack_path)
                return True
        return False

    def emit_doubt(self, claim_hash: str, reason: str):
        """Inyecta un estado de Duda Metódica en el flujo del bus."""
        self.publish("COGNITIVE_DOUBT", {"target": claim_hash, "reason": reason}, sender="SECURITY_QA")

bus = EventBus()
