# Swarm Intelligence Report (RSI Cycle v3.0 — Real Stress)

Date: 2026-03-10  
System: i9 + RTX 3060 (6GB)  
Repo: `AgentOrquestor` (core v3.5)

## 1) Diagnóstico de Colapso Sistémico

### Saturación de Bus (I/O de `stderr`)
- Con 4+ agentes emitiendo telemetría masiva, `stderr` se convierte en cuello de botella (I/O bloqueante).
- Mitigación aplicada:
  - `core/event_bus.py`: `EVENTBUS_STDERR=0` por defecto (activar con `EVENTBUS_STDERR=1`).
  - `core/telemetry.py`: `TELEMETRY_STDERR=0` desactiva el handler a `stderr` y deja JSONL como fuente de verdad.

### Pérdida de “intuición” del enjambre en OOM
- Si el proceso muere (OOM/segfault) durante presión de VRAM, los últimos eventos críticos se pueden perder si no son durables.
- Mitigación aplicada:
  - `core/event_bus.py`: persist-before-dispatch (eventos “inmortales” antes del dispatch).
  - Replay: `bus.replay_persisted_events()` (bootstrap best-effort en `core/graph.py`).

### Hipótesis recurrentes (Deriva cognitiva)
- En reintentos, los agentes tienden a repetir el mismo diagnóstico → inflación de contexto y tokens.
- Mitigación aplicada:
  - `core/shredder.py`: poda por similitud `>= 0.85`; en la 3ra repetición reemplaza por “LESSON”.

### Contención en Bóveda / Persistencia
- Riesgo: locks globales (o directorios “hotspot”) bajo swarm rompen la reactividad.
- Mitigación aplicada:
  - `core/memory_manager.py`: sharding de snapshots por `task_id`.
  - `core/persistence.py`: soporte para lock sharding (`acquire_db_lock(task_id=...)`) si se activa en rutas DB.

## 2) Stress Experience Generated (Harness)

Script: `scripts/stress_harness.py`

Workload simulated:
- 5 concurrent “trading missions” (XAUUSD) emitting `TASK_RECEIVED`, `PLAN_GENERATED`, `TEST_FAILED`
- 3× `VRAM_THRESHOLD_REACHED`
- 1× `SYSTEM_ERROR_DETECTED`

Artifacts produced:
- Telemetry log: `.cortex/logs/telemetry.jsonl`
- Durable bus queue: `.cortex/bus_buffer.jsonl` (override: `EVENTBUS_QUEUE_PATH=.cortex/bus_buffer.queue`)

## 3) Drift Analysis (Semantic Pruning Impact)

Implementation: `core/shredder.py`

Mechanism:
- Normalizes AI message text and detects repetition with similarity `>= 0.85`.
- On 3rd repetition of the same hypothesis, replaces the message with a compact “LESSON” (keeps only learned signal).
- Tracks savings in `dtg_context` and emits telemetry event `PRUNED_CIRCULAR_REASONING`.

Observed on the last stress run (telemetry window ≈ 1s around `STRESS_RUN_COMPLETE`):
- Pruning events: **5**
- Estimated tokens saved: **9140**
- Baseline tokens (estimated from repeated hypothesis × missions): **27810**
- Estimated token savings: **32.87%**

## 4) Hardware Heat Map (VRAM Pressure Response)

Stress harness emitted repeated VRAM pressure markers:

| Sample | used_mb | threshold_mb | status |
|---:|---:|---:|---|
| 1 | 5900 | 5700 | breached |
| 2 | 5925 | 5700 | breached |
| 3 | 5950 | 5700 | breached |

Key observation:
- With the **durable bus queue**, VRAM pressure events are persisted before dispatch, preserving the “last known state” even if the process dies during OOM.

## 5) Buffer de Emergencia Durable (Second-Order)

Implementation: `core/event_bus.py` (+ bootstrap in `core/graph.py`)

Design:
- Append-only durable queue: `.cortex/bus_buffer.jsonl` (persist-before-dispatch).
- Replay mechanism: `bus.replay_persisted_events()`; automatically scheduled best-effort in `core/graph.py` when the asyncio loop is running.
- ACK tracking uses a durable **byte offset** in `.cortex/bus_buffer.ack` (override: `EVENTBUS_ACK_PATH=...`) to resume after a crash.

Semantics:
- **At-least-once delivery** across restarts (safe under crash; duplicates possible if ACK lags).
- Tunables (env):
  - `EVENTBUS_FSYNC_EVERY_N` (durability vs throughput)
  - `EVENTBUS_ACK_EVERY_N` / `EVENTBUS_ACK_MAX_SECONDS` (duplicate window vs throughput)
  - `EVENTBUS_STDERR` / `TELEMETRY_STDERR` (control de cuello I/O)

## 6) Vault Sharding (10 missions parallel readiness)

Implementation: `core/memory_manager.py`

Change:
- Snapshots now shard by `task_id`:
  - `.cortex/snapshots/<task_id>/manifesto_<ts>_<uuid>.json`

Impact:
- Reduces directory hotspotting and prepares the vault for per-task locking (Pareto win under parallel workloads).

## 7) Swarm Immunity Certificate (Post_Task_Validator)

Implementation: `agents/skills/validator/executor.py`

Certification added:
- Validates `EventBus` persistent publish throughput with a 1000-event burst.
- Measured throughput (local run): **6836.26 events/sec** (target ≥ 500 events/sec).

## 8) Multimodal Expansion Plan (RTX 3060 + Meta Ads Images)

Goal: process Meta Ads images without blocking the main reasoning loop.

Proposed architecture:
- **Async multimodal worker** (separate asyncio task / process):
  - pulls image jobs from a queue
  - enforces VRAM budget (batch size + concurrency = 1..2 on 6GB)
  - writes results into `.cortex/multimodal/<task_id>/...`
- **Main loop stays CPU-bound**:
  - schedules jobs
  - consumes completed embeddings/labels via event bus events (persisted)
- Backpressure policy:
  - when VRAM pressure events occur, pause multimodal worker and only persist minimal “lesson + manifest”.

## 9) Wisdom KPI (Self-Correction Without Human)

This RSI cycle produced:
- **5** autonomous self-corrections (`PRUNED_CIRCULAR_REASONING`) in the stress window.

## 10) Autonomy Certificate (Crash Survival)

Criteria:
- Events persisted pre-dispatch (`.cortex/bus_buffer.jsonl` exists and is append-only).
- Replay capability exists (`bus.replay_persisted_events()`), enabling recovery after hard crashes.
- Vault snapshots shard by `task_id`, preserving “consciousness manifest” per mission.

Status:
- Durable queue + replay + sharded snapshots are implemented; system can resume after crash with at-least-once semantics.

### MCP Audit (Third-Level)

Tools invoked:
- `mcp__AgentOrquestor__semantic_audit` → `{"status":"OK"}`
- `mcp__AgentOrquestor__direct_refactor` → `{"status":"OK"}`
