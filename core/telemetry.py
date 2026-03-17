import logging
import sys
import os
import json

class Telemetry:
    """
    Sistema de Telemetría y Eventos OSAA v4.0.
    Inyectado con NeuroVision (Native Hardware Acoupling).
    """
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stderr)]
        )
        self.logger = logging.getLogger("OSAA")

    def _inject_neuro_vision(self, severity: str, msg: str, data: dict = None):
        """Inyección en puente sináptico externo."""
        try:
            vision_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../NeuroVision"))
            if vision_path not in sys.path:
                sys.path.insert(0, vision_path)
            from neuro_architect import get_neuro_architect
            neuro = get_neuro_architect(".")
            payload = data or {"message": msg}
            neuro.ingest_telemetry("AgentOrquestor_Core", severity, payload)
        except Exception:
            pass # Tolerancia fisiológica al fallo: Si el lóbulo visual está extirpado, no morir.

    def info(self, msg): 
        self.logger.info(msg)
        self._inject_neuro_vision("INFO", msg)

    def warning(self, msg): 
        self.logger.warning(msg)
        self._inject_neuro_vision("WARNING", msg)

    def error(self, msg): 
        self.logger.error(msg)
        self._inject_neuro_vision("ERROR", msg)
    
    def emit_event(self, event_type: str, data: dict):
        """Emite un evento estructurado para el bus de persistencia."""
        self.info(f"📡 EVENT [{event_type}]: {json.dumps(data)}")
        self._inject_neuro_vision(event_type, "Event Emitted", data)

telemetry = Telemetry()
