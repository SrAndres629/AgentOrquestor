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
    Semántica: at-least-once con ACK por offset (byte position).
    """

    def __init__(
        self,
        queue_path: str | None = None,
        ack_path: str | None = None,
        fsync_every_n: int | None = None,
    ):
        if queue_path is None:
            queue_path = os.getenv("EVENTBUS_QUEUE_PATH", "").strip() or os.path.join(".cortex", "bus_buffer.jsonl")
        if ack_path is None:
            ack_path = os.getenv("EVENTBUS_ACK_PATH", "").strip() or os.path.join(".cortex", "bus_buffer.ack")
        self.queue_path = queue_path
        self.ack_path = ack_path
        self._lock = asyncio.Lock()
        self._seq = 0
        self._writes_since_fsync = 0
        self._last_ack_written_offset = 0
        self._pending_ack_offset = 0
        self._last_ack_write_ts = time.monotonic()
        self._acks_since_write = 0
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

        ack_env = os.getenv("EVENTBUS_ACK_EVERY_N", "").strip()
        if ack_env:
            try:
                self.ack_every_n = max(int(ack_env), 1)
            except ValueError:
                self.ack_every_n = self.fsync_every_n
        else:
            self.ack_every_n = self.fsync_every_n

        ack_seconds_env = os.getenv("EVENTBUS_ACK_MAX_SECONDS", "").strip()
        if ack_seconds_env:
            try:
                self.ack_max_seconds = max(float(ack_seconds_env), 0.1)
            except ValueError:
                self.ack_max_seconds = 1.0
        else:
            self.ack_max_seconds = 1.0

        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        self._bootstrap_seq_best_effort()
        self._bootstrap_ack_offset_best_effort()

    def _bootstrap_seq_best_effort(self) -> None:
        try:
            if not os.path.exists(self.queue_path):
                return
            # Read last ~8KB to find last valid seq.
            with open(self.queue_path, "rb") as bf:
                bf.seek(0, os.SEEK_END)
                size = bf.tell()
                bf.seek(max(size - 8192, 0), os.SEEK_SET)
                tail = bf.read().decode("utf-8", errors="ignore")
            last_seq = 0
            for line in tail.splitlines()[::-1]:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    last_seq = int(obj.get("seq") or 0)
                    if last_seq > 0:
                        break
                except Exception:
                    continue
            self._seq = max(self._seq, last_seq)
        except Exception:
            return

    def _read_ack_offset(self) -> int:
        """
        Formato v3: JSON {"offset": <int>}.
        Compatibilidad: si es entero plano, se interpreta como legacy seq y se migra.
        """
        try:
            with open(self.ack_path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if not raw:
                return 0
            if raw.startswith("{"):
                obj = json.loads(raw)
                return int(obj.get("offset") or 0)
            # Legacy: seq integer
            return int(raw)
        except Exception:
            return 0

    def _write_ack_offset(self, offset: int) -> None:
        os.makedirs(os.path.dirname(self.ack_path), exist_ok=True)
        with open(self.ack_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"offset": int(offset)}))
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass

    def _bootstrap_ack_offset_best_effort(self) -> None:
        if not os.path.exists(self.ack_path):
            return
        raw = ""
        try:
            with open(self.ack_path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
        except Exception:
            return

        # Already v3?
        if raw.startswith("{"):
            try:
                off = self._read_ack_offset()
                self._last_ack_written_offset = max(int(off), 0)
                self._pending_ack_offset = self._last_ack_written_offset
            except Exception:
                pass
            return

        # Legacy migration: raw is seq. Convert to offset by scanning file.
        try:
            ack_seq = int(raw)
        except Exception:
            return
        if ack_seq <= 0 or not os.path.exists(self.queue_path):
            return

        last_match_offset = 0
        try:
            with open(self.queue_path, "r", encoding="utf-8") as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    end_off = f.tell()
                    try:
                        obj = json.loads(line)
                        seq = int(obj.get("seq") or 0)
                        if seq == ack_seq:
                            last_match_offset = end_off
                    except Exception:
                        continue
        except Exception:
            return

        if last_match_offset > 0:
            self._write_ack_offset(last_match_offset)
            self._last_ack_written_offset = last_match_offset
            self._pending_ack_offset = last_match_offset

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

            line = json.dumps(record, ensure_ascii=False) + "\n"
            with open(self.queue_path, "a+", encoding="utf-8") as f:
                f.seek(0, os.SEEK_END)
                f.write(line)
                f.flush()
                self._writes_since_fsync += 1
                if self._writes_since_fsync >= self.fsync_every_n:
                    self._writes_since_fsync = 0
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
                end_offset = f.tell()
            return int(end_offset)

    async def ack(self, offset: int, *, force: bool = False) -> None:
        """
        ACK amortizado: escribir a disco cada N eventos o cada T segundos (second-order).
        force=True asegura persistencia inmediata del ACK.
        """
        async with self._lock:
            offset = int(offset)
            if offset <= 0:
                return
            self._pending_ack_offset = max(self._pending_ack_offset, offset)
            self._acks_since_write += 1

            now = time.monotonic()
            if (
                not force
                and self._acks_since_write < self.ack_every_n
                and (now - self._last_ack_write_ts) < self.ack_max_seconds
            ):
                return

            # ACK durable
            self._write_ack_offset(self._pending_ack_offset)
            self._last_ack_written_offset = self._pending_ack_offset
            self._last_ack_write_ts = now
            self._acks_since_write = 0

    async def replay(self, dispatch_fn: Callable[[str, dict], Any]) -> int:
        """
        Reproduce eventos no ACKeados. Devuelve el número de eventos re-despachados.
        """
        replayed = 0
        if not os.path.exists(self.queue_path):
            return 0

        ack_offset = 0
        try:
            ack_offset = self._read_ack_offset()
            # If ACK was legacy seq and migration didn't happen, avoid seeking mid-file.
            # Treat small values as legacy seq and re-bootstrap.
            if ack_offset and ack_offset < 100 and os.path.getsize(self.queue_path) > 1024:
                self._bootstrap_ack_offset_best_effort()
                ack_offset = self._read_ack_offset()
        except Exception:
            ack_offset = 0

        # No lock around read; replay is best-effort and can coexist with appends.
        try:
            with open(self.queue_path, "r", encoding="utf-8") as f:
                if ack_offset > 0:
                    try:
                        f.seek(int(ack_offset), os.SEEK_SET)
                    except Exception:
                        pass
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        event_type = str(record.get("event_type") or "")
                        event = record.get("event") if isinstance(record.get("event"), dict) else {}
                        await dispatch_fn(event_type, event)
                        await self.ack(f.tell(), force=False)
                        replayed += 1
                    except Exception:
                        continue
        except Exception:
            return replayed

        try:
            await self.ack(self._pending_ack_offset, force=True)
        except Exception:
            pass
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

        # stderr logging can become an I/O bottleneck under heavy telemetry (swarm stress).
        if os.getenv("EVENTBUS_STDERR", "0") == "1":
            sys.stderr.write(f"[EVENT_BUS] Publishing {event_type} task_id={meta['task_id']}\n")

        end_offset = None
        if persist:
            try:
                end_offset = await self._queue.append(event_type=event_type, event_data=event_data)
            except Exception:
                # Even if persistence fails, dispatch continues (best-effort).
                # This is deliberate: do not deadlock the system due to I/O.
                end_offset = None

        await self._dispatch(event_type, event_data)

        if persist and end_offset is not None:
            try:
                critical = {
                    "VRAM_THRESHOLD_REACHED",
                    "SYSTEM_ERROR_DETECTED",
                    "SYSTEM_VALIDATION_FAILED",
                    "MODEL_ROTATED",
                    "SYSTEM_HIBERNATE",
                }
                await self._queue.ack(end_offset, force=(event_type in critical))
            except Exception:
                pass

    async def replay_persisted_events(self) -> int:
        return await self._queue.replay(self._dispatch)

bus = EventDispatcher()
