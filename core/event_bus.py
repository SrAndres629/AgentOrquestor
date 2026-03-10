import sys
import asyncio
import time
from enum import Enum
from typing import Callable, Dict, List, Any

class EventType(Enum):
    TASK_RECEIVED = "TASK_RECEIVED"
    PLAN_GENERATED = "PLAN_GENERATED"
    CODE_IMPLEMENTED = "CODE_IMPLEMENTED"
    TEST_FAILED = "TEST_FAILED"
    VRAM_THRESHOLD_REACHED = "VRAM_THRESHOLD_REACHED"
    NODE_STARTED = "NODE_STARTED"
    NODE_COMPLETED = "NODE_COMPLETED"
    EVENT_MISSING_CAPABILITY = "EVENT_MISSING_CAPABILITY"

class EventDispatcher:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    async def publish(self, event_type: str, data: Any = None, task_id: str | None = None, correlation_id: str | None = None):
        meta = {
            "task_id": task_id or "unknown",
            "correlation_id": correlation_id or task_id or "unknown",
            "ts": time.time(),
        }

        if isinstance(data, dict):
            event_data = dict(data)
            event_data["_meta"] = meta
        else:
            event_data = {"payload": data, "_meta": meta}

        sys.stderr.write(f"[EVENT_BUS] Publishing {event_type} task_id={meta['task_id']}\n")
        if event_type in self._listeners:
            tasks = [callback(event_data) for callback in self._listeners[event_type]]
            if tasks:
                await asyncio.gather(*tasks)

bus = EventDispatcher()
