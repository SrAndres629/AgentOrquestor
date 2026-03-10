import sys
import asyncio
import time
import os
import json
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

class _EventDiskQueue:
    """
    Cola durable (append-only) para eventos del bus.
    Semántica: at-least-once con ACK por secuencia.
    """

    def __init__(
        self,
        queue_path: str = os.path.join(".cortex", "bus_buffer.jsonl"),
        ack_path: str = os.path.join(".cortex", "bus_buffer.ack"),
        fsync_every_n: int | None = None,
    ):
        self.queue_path = queue_path
        self.ack_path = ack_path
        self._lock = asyncio.Lock()
        self._seq = 0
        self._writes_since_fsync = 0
        # Second-order: fsync is expensive. Default keeps critical durability
        # while still allowing high throughput (validator can tune env).
        if fsync_every_n is None:
            env = os.getenv("EVENTBUS_FSYNC_EVERY_N", "").strip()
            if env:
                try:
                    fsync_every_n = int(env)
                except ValueError:
                    fsync_every_n = 25
            else:
                fsync_every_n = 25
        self.fsync_every_n = max(int(fsync_every_n), 1)

        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)

    def _read_ack_seq(self) -> int:
        try:
            with open(self.ack_path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            return int(raw) if raw else 0
        except Exception:
            return 0

    def _write_ack_seq(self, seq: int) -> None:
        os.makedirs(os.path.dirname(self.ack_path), exist_ok=True)
        with open(self.ack_path, "w", encoding="utf-8") as f:
            f.write(str(int(seq)))
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass

    async def append(self, event_type: str, event_data: dict) -> int:
        async with self._lock:
            self._seq += 1
            seq = self._seq

            record = {
                "seq": seq,
                "ts": time.time(),
                "event_type": event_type,
                "event": event_data,
            }

            with open(self.queue_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                self._writes_since_fsync += 1
                if self._writes_since_fsync >= self.fsync_every_n:
                    self._writes_since_fsync = 0
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
            return seq

    async def ack(self, seq: int) -> None:
        # ACK is sync on disk: if we claim it's processed, we want it durable.
        async with self._lock:
            current = self._read_ack_seq()
            if seq > current:
                self._write_ack_seq(seq)

    async def replay(self, dispatch_fn: Callable[[str, dict], Any]) -> int:
        """
        Reproduce eventos no ACKeados. Devuelve el número de eventos re-despachados.
        """
        ack_seq = self._read_ack_seq()
        replayed = 0
        if not os.path.exists(self.queue_path):
            return 0

        # No lock around read; replay is best-effort and can coexist with appends.
        try:
            with open(self.queue_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        seq = int(record.get("seq") or 0)
                        if seq <= ack_seq:
                            continue
                        event_type = str(record.get("event_type") or "")
                        event = record.get("event") if isinstance(record.get("event"), dict) else {}
                        await dispatch_fn(event_type, event)
                        await self.ack(seq)
                        replayed += 1
                    except Exception:
                        continue
        except Exception:
            return replayed

        return replayed

class EventDispatcher:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._queue = _EventDiskQueue()

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    async def _dispatch(self, event_type: str, event_data: dict) -> None:
        if event_type in self._listeners:
            tasks = [callback(event_data) for callback in self._listeners[event_type]]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=False)

    async def publish(
        self,
        event_type: str,
        data: Any = None,
        task_id: str | None = None,
        correlation_id: str | None = None,
        *,
        persist: bool = True,
    ):
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

        if os.getenv("EVENTBUS_STDERR", "1") == "1":
            sys.stderr.write(f"[EVENT_BUS] Publishing {event_type} task_id={meta['task_id']}\n")

        seq = None
        if persist:
            try:
                seq = await self._queue.append(event_type=event_type, event_data=event_data)
            except Exception:
                # Even if persistence fails, dispatch continues (best-effort).
                # This is deliberate: do not deadlock the system due to I/O.
                seq = None

        await self._dispatch(event_type, event_data)

        if persist and seq is not None:
            try:
                await self._queue.ack(seq)
            except Exception:
                pass

    async def replay_persisted_events(self) -> int:
        return await self._queue.replay(self._dispatch)

bus = EventDispatcher()
