import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class _Snapshot:
    proponent: str = ""
    adversary: str = ""
    vram_line: str = ""
    bus_tail: str = ""


def _tail_lines(path: str, n: int = 200) -> list[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            chunk = 8192
            data = b""
            pos = size
            while pos > 0 and data.count(b"\n") < n + 1:
                pos = max(0, pos - chunk)
                f.seek(pos)
                data = f.read(size - pos) + data
                size = pos
        lines = data.decode("utf-8", errors="ignore").splitlines()
        return lines[-n:]
    except Exception:
        return []


def _extract_latest(snapshot: _Snapshot) -> _Snapshot:
    bus_path = os.getenv("EVENTBUS_QUEUE_PATH", "").strip() or os.path.join(".cortex", "bus_buffer.jsonl")
    tel_path = os.path.join(".cortex", "logs", "telemetry.jsonl")

    bus_lines = _tail_lines(bus_path, n=300)
    pro = ""
    adv = ""
    tail_events = []
    for line in reversed(bus_lines):
        try:
            obj = json.loads(line)
            et = obj.get("event_type")
            ev = obj.get("event") if isinstance(obj.get("event"), dict) else {}
            if not pro and et == "DIALECTIC_PROPONENT":
                pro = str(ev.get("content") or "")
            if not adv and et == "DIALECTIC_ADVERSARY":
                adv = str(ev.get("content") or "")
            if et:
                tail_events.append(str(et))
            if pro and adv and len(tail_events) >= 30:
                break
        except Exception:
            continue

    tel_lines = _tail_lines(tel_path, n=200)
    vram_line = ""
    for line in reversed(tel_lines):
        if "\"event\": \"STRESS_VRAM\"" in line or "\"event\":\"STRESS_VRAM\"" in line or "VRAM" in line:
            vram_line = line.strip()[:180]
            break

    snapshot.proponent = pro or snapshot.proponent
    snapshot.adversary = adv or snapshot.adversary
    snapshot.vram_line = vram_line or snapshot.vram_line
    snapshot.bus_tail = " | ".join(reversed(tail_events[:12]))
    return snapshot


def run_war_room() -> None:
    """
    Textual-based War Room (2-panel dialectic + bus/vram tail).
    This module is optional; it only runs if `textual` is installed.
    """
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Footer, Header, Static
    except Exception as e:
        raise SystemExit(
            "Missing dependency: textual.\n"
            "Install in your venv and run again.\n"
            f"Import error: {e}"
        )

    class WarRoom(App):
        CSS = """
        Screen { layout: vertical; }
        #top { height: 1fr; }
        #bottom { height: 6; }
        .panel { border: round $accent; padding: 1; }
        """

        def __init__(self) -> None:
            super().__init__()
            self.snapshot = _Snapshot()

        def compose(self) -> ComposeResult:
            yield Header()
            with Horizontal(id="top"):
                with Vertical(classes="panel"):
                    yield Static("Proponente (Lead Dev)", id="title_left")
                    yield Static("", id="proponent")
                with Vertical(classes="panel"):
                    yield Static("Adversario (Security/QA)", id="title_right")
                    yield Static("", id="adversary")
            with Vertical(id="bottom", classes="panel"):
                yield Static("EventBus tail", id="bus_tail")
                yield Static("VRAM", id="vram")
            yield Footer()

        def on_mount(self) -> None:
            self.set_interval(0.5, self._tick)

        def _tick(self) -> None:
            self.snapshot = _extract_latest(self.snapshot)
            self.query_one("#proponent", Static).update(self.snapshot.proponent[-4000:] or "(waiting...)")
            self.query_one("#adversary", Static).update(self.snapshot.adversary[-4000:] or "(waiting...)")
            self.query_one("#bus_tail", Static).update(self.snapshot.bus_tail or "(no events yet)")
            self.query_one("#vram", Static).update(self.snapshot.vram_line or "(no vram yet)")

    WarRoom().run()


if __name__ == "__main__":
    run_war_room()

