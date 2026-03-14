# AgentOrquestor v5.0 — Sovereign Swarm Evolution 🧬

**AgentOrquestor** is an autonomous evolutionary organim designed under the **OSAA v5.0 (Autonomous Sovereign Agent Architecture)** protocol. It transforms a group of isolated LLM actors into a unified, self-improving swarm capable of hardware perception, metabolic resilience, and capability bootstrapping.

## Core Architecture

### 1. Inception Layer (`ignite.py`)
The entry point that audits user goals and situational context. It triggers **Misión Cero** if capabilities are missing.

### 2. Orchestration Layer (`core/swarm_launcher.py`)
Manages the distributed lifecycle of the swarm.
- **BrainForge**: Generates agent brains dynamically, ingesting lecciones from previous iterations (`handoff_state.md`).
- **ConsensusWatchdog**: Monitors the Event Bus to prevent deadlocks and manages graceful teardown of isolated terminals.
- **HandoffRouter**: Strategically decides between sealing a mission (Consensus) or pivoting (Handoff) for re-iteration.

### 3. Metabolic Layer (`scripts/agent_runner.py`)
The inference daemon running in isolated `tmux` sessions.
- **Exponential Backoff**: Resilient handling of LLM provider rate limits (HTTP 429).
- **Graceful Asphyxiation**: Atomic signaling of network failure to the swarm bus before exit.
- **Sovereignty Tools**: Built-in capabilities like `register_new_tool` for on-the-fly capability integration.

### 4. Evolutionary Layer (`core/mission_planner.py`)
- **MissionPlanner**: Audits arsenal (MCP/Skills) and plans self-fabrication missions, triggering Misión Cero when required.
- **Persistence (Ley 3)**: Long-term capability memory is persisted in `agents/registry.yaml` and mission outcomes are handled via handoff logs.

## Usage

Ignite a mission with a natural language goal:
```bash
python3 ignite.py --goal "Analiza el tráfico de red del servidor y optimiza endpoints"
```

---
*Developed by the Architect and the Swarm. Total Sovereignty Mode Enabled.*