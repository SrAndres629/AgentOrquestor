import asyncio
import hashlib
import os
import random
import sys
import time
from types import SimpleNamespace

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.event_bus import bus
from core.shredder import shredder
from core.telemetry import telemetry


def _task_id(objective: str) -> str:
    return hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12]


def _silence_stdout() -> None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


async def _simulate_trading_mission(idx: int) -> None:
    objective = f"trade:XAUUSD mission={idx} strategy=mean_reversion"
    task_id = _task_id(objective)
    correlation_id = f"{task_id}:{idx}"

    manifest = SimpleNamespace(objective=objective, kpis={"pnl": "mock"}, token_budget=50_000)
    filler = (
        "RISK: latency spikes; slippage; regime shift. "
        "CHECK: orderbook imbalance; volatility clustering; spread mean. "
        "ERROR: if no new evidence, do not restate the same hypothesis. "
    )
    repeated_hypothesis = (
        "HYPOTHESIS: Spread widening implies mean reversion entry.\n"
        + ("DETAIL: " + filler) * 40
        + "\nEVIDENCE: synthetic.\nACTION: wait for confirmation.\n"
        + "LESSON: avoid repeating identical hypothesis without new evidence."
    )
    # Force redundancy patterns for pruning logic (post-refactor).
    messages = [
        SimpleNamespace(type="human", content=f"Objective: {objective}"),
        SimpleNamespace(type="ai", content=repeated_hypothesis),
        SimpleNamespace(type="ai", content=repeated_hypothesis),
        SimpleNamespace(type="ai", content=repeated_hypothesis),
    ]
    state = {
        "task_manifest": {"objective": manifest.objective, "kpis": manifest.kpis, "token_budget": manifest.token_budget},
        "dtg_context": {},
        "messages": messages,
    }

    await bus.publish("TASK_RECEIVED", data={"objective": objective}, task_id=task_id, correlation_id=correlation_id)
    telemetry.emit_event("STRESS_TASK_STARTED", {"objective": objective, "task_id": task_id}, correlation_id=correlation_id)

    await bus.publish("PLAN_GENERATED", data={"plan": "synthetic-plan-v1"}, task_id=task_id, correlation_id=correlation_id)
    telemetry.emit_event("STRESS_PLAN", {"redundant_hypothesis": repeated_hypothesis}, correlation_id=correlation_id)

    # Apply shredder (will become drift-aware after refactor).
    await shredder.shred(state)

    # Simulate a failure path (5 missions will “fail”).
    await bus.publish(
        "TEST_FAILED",
        data={"error": "synthetic-backtest-failed", "retryable": True, "hypothesis": repeated_hypothesis},
        task_id=task_id,
        correlation_id=correlation_id,
    )
    telemetry.emit_event("STRESS_TASK_FAILED", {"task_id": task_id, "reason": "synthetic"}, correlation_id=correlation_id)


async def _emit_system_pressure_events() -> None:
    # Emit repeated VRAM pressure to force “crash-resilience” event patterns.
    for j in range(3):
        used = 5_900 + j * 25
        thr = 5_700
        await bus.publish(
            "VRAM_THRESHOLD_REACHED",
            data={"vram_usage_mb": used, "threshold_mb": thr, "note": "synthetic-vram-pressure"},
            task_id="system",
            correlation_id=f"vram:{j}",
        )
        telemetry.emit_event("STRESS_VRAM", {"used_mb": used, "threshold_mb": thr}, correlation_id=f"vram:{j}")
        await asyncio.sleep(0.01)

    await bus.publish(
        "SYSTEM_ERROR_DETECTED",
        data={"error": "synthetic:OOM during parallel missions", "severity": "HIGH"},
        task_id="system",
        correlation_id="system:error:0",
    )
    telemetry.emit_event("STRESS_SYSTEM_ERROR", {"error": "synthetic:OOM"}, correlation_id="system:error:0")


async def main() -> int:
    _silence_stdout()
    os.environ.setdefault("EVENTBUS_STDERR", "0")
    os.environ.setdefault("TELEMETRY_STDERR", "0")
    random.seed(1337)

    t0 = time.time()
    missions = [_simulate_trading_mission(i) for i in range(1, 6)]
    await asyncio.gather(*missions)
    await _emit_system_pressure_events()

    telemetry.emit_event("STRESS_RUN_COMPLETE", {"elapsed_s": round(time.time() - t0, 4)}, correlation_id="stress:run")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as e:
        sys.stderr.write(f"[stress_harness] fatal: {e}\n")
        raise
