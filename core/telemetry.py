import sys
import logging
import json
import os
import time
from typing import Any

class UnifiedTelemetry:
    def __init__(self):
        self.logger = logging.getLogger('AgentOrquestor')
        self.logger.propagate = False
        # stderr logging can become an I/O bottleneck under swarm stress.
        # Keep JSONL telemetry as the source of truth; gate stderr via env.
        stderr_enabled = os.getenv("TELEMETRY_STDERR", "1").strip() == "1"
        if stderr_enabled and not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self._jsonl_path = os.path.join(".cortex", "logs", "telemetry.jsonl")

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def emit_event(self, event_name: str, data: Any, correlation_id: str | None = None):
        payload = {
            "ts": time.time(),
            "event": event_name,
            "correlation_id": correlation_id,
            "data": data,
        }
        try:
            os.makedirs(os.path.dirname(self._jsonl_path), exist_ok=True)
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Nunca romper el transporte por fallos de logging
            pass
        self.logger.info(f"🔔 [EVENT] {event_name}: {data}")

telemetry = UnifiedTelemetry()
