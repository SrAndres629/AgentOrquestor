import logging
import sys
import json

class Telemetry:
    """
    Sistema de Telemetría y Eventos OSAA v4.0.
    """
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stderr)]
        )
        self.logger = logging.getLogger("OSAA")

    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    
    def emit_event(self, event_type: str, data: dict):
        """Emite un evento estructurado para el bus de persistencia."""
        self.info(f"📡 EVENT [{event_type}]: {json.dumps(data)}")

telemetry = Telemetry()
