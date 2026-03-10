import sys
import logging
from typing import Any

class UnifiedTelemetry:
    def __init__(self):
        self.logger = logging.getLogger('AgentOrquestor')
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def emit_event(self, event_name: str, data: Any):
        # Notificación silenciosa en stderr
        sys.stderr.write(f'🔔 [EVENT] {event_name}: {data}
')
        sys.stderr.flush()

telemetry = UnifiedTelemetry()
