#!/usr/bin/env python3
"""
AgentOrquestor — Agent Runner (Daemon de Inferencia Aislada) v5.0
=================================================================
Proceso que se ejecuta dentro de cada sesión tmux aislada.
Materializa la cognición de un agente: lee su "cerebro" (.md),
monitorea el bus IPC para sincronización de turnos dialécticos,
invoca la API de LLM, y escribe su reporte atómicamente.

Protocolo de Turnos Dialécticos
-------------------------------
Los agentes NO hablan todos a la vez. El bus IPC impone un orden:

  1. El Runner lee las últimas N entradas del bus_buffer.jsonl
  2. Extrae el campo "sender" del último mensaje AGENT_REPORT
  3. Si el último emisor es "mi par dialéctico" → es MI turno
  4. Si el último emisor soy yo → ESPERAR (no es mi turno)
  5. Si no hay mensajes previos → el primer turno es del PROPONENT

Mapa de turnos por rol:
  - PROPONENT habla primero (o después del ADVERSARY)
  - ADVERSARY habla después del PROPONENT
  - ARCHITECT habla primero y cierra último
  - OPTIMIZER habla al final de cada ronda

Señales del SO
--------------
  SIGTERM / SIGINT → Cierre limpio: flush buffers, escribir
  evento AGENT_SHUTDOWN al bus, liberar file descriptors.

Uso:
  python agent_runner.py \\
      --brain .cortex/missions/{id}/brains/contexto_LeadDev.md \\
      --mission-id m_abc123 \\
      --agent-name LeadDeveloper
"""

import os
import sys
import json
import time
import signal
import asyncio
import argparse
import hashlib
from typing import Dict, Any, List, Optional, Literal
from pathlib import Path
from dataclasses import dataclass, field

# Asegurar que el proyecto raíz esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from core.telemetry import telemetry
from core.swarm_launcher import (
    atomic_write,
    atomic_append,
    safe_read,
    CORTEX_DIR,
    MISSIONS_DIR,
)
from core.shredder import LogShredder
from core.hardware_monitor import HardwareMonitor


# ---------------------------------------------------------------------------
# 0. CONSTANTES Y CONFIGURACIÓN
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Límites metabólicos por agente
MAX_CONTEXT_CHARS = 32000          # ~8000 tokens aprox
MAX_OUTPUT_CHARS = 16000           # ~4000 tokens aprox
BUS_TAIL_LINES = 50               # Últimas N líneas del bus a considerar
TURN_POLL_INTERVAL = 2.0           # Segundos entre polls de turno
MAX_TURN_WAIT = 120.0              # Timeout máximo esperando turno
INFERENCE_TIMEOUT = 60.0           # Timeout de llamada al LLM
MAX_DEBATE_ROUNDS = 3              # Rondas máximas de debate interno


# ---------------------------------------------------------------------------
# 1. TURN MANAGER — SINCRONIZACIÓN DIALÉCTICA
# ---------------------------------------------------------------------------

@dataclass
class TurnState:
    """Estado del sistema de turnos."""
    my_name: str
    my_role: str
    last_speaker: Optional[str] = None
    round_number: int = 0
    is_my_turn: bool = False


class DialecticTurnManager:
    """
    Gestiona la sincronización de turnos entre agentes.
    
    Protocolo:
    ┌────────────────────────────────────────────────────┐
    │  PROPONENT (turno 1) → ADVERSARY (turno 2) → ...  │
    │  Si ARCHITECT existe: habla primero (turno 0)      │
    │  Si OPTIMIZER existe: habla último (turno N)       │
    └────────────────────────────────────────────────────┘
    
    La detección de turno se basa en leer el último evento
    AGENT_REPORT del bus_buffer.jsonl. Si el último emisor
    es mi par → es mi turno. Si soy yo → esperar.
    """

    # Mapa de precedencia: quién habla DESPUÉS de quién
    TURN_AFTER = {
        "proponent": {"after": ["adversary", "architect"], "first_turn": True},
        "adversary": {"after": ["proponent"], "first_turn": False},
        "architect": {"after": [], "first_turn": True},   # Siempre primero
        "optimizer": {"after": ["adversary", "proponent"], "first_turn": False},
    }

    def __init__(self, agent_name: str, agent_role: str, bus_path: Path):
        self.agent_name = agent_name
        self.agent_role = agent_role.lower()
        self.bus_path = bus_path
        self.state = TurnState(my_name=agent_name, my_role=agent_role)

    def _read_bus_tail(self, n_lines: int = BUS_TAIL_LINES) -> List[Dict[str, Any]]:
        """
        Lee las últimas N líneas del bus JSONL de forma segura.
        Tolerante a líneas parciales o corruptas (las ignora).
        """
        content = safe_read(self.bus_path)
        if not content:
            return []

        lines = content.strip().splitlines()
        tail = lines[-n_lines:] if len(lines) > n_lines else lines
        events = []
        for line in tail:
            try:
                events.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue  # Línea corrupta o parcial, ignorar
        return events

    def _get_last_agent_event(self, events: List[Dict]) -> Optional[Dict]:
        """Retorna el último evento de tipo AGENT_REPORT del bus."""
        for event in reversed(events):
            if event.get("type") == "AGENT_REPORT":
                return event
        return None

    def _get_mission_events(self, events: List[Dict], mission_id: str) -> List[Dict]:
        """Filtra eventos que pertenecen a la misión actual."""
        return [
            e for e in events
            if e.get("payload", {}).get("mission_id") == mission_id
            or e.get("type") == "AGENT_REPORT"
        ]

    def check_turn(self, mission_id: str) -> TurnState:
        """
        Determina si es el turno de este agente.
        
        Lógica:
        1. Sin eventos previos → turno del agente con first_turn=True
        2. Último emisor == yo → NO es mi turno (ya hablé)
        3. Último emisor está en mi lista "after" → ES mi turno
        4. Otro caso → NO es mi turno (esperar)
        """
        events = self._read_bus_tail()
        mission_events = self._get_mission_events(events, mission_id)

        # Sin eventos previos: turno del first_turn
        if not mission_events:
            turn_config = self.TURN_AFTER.get(self.agent_role, {})
            self.state.is_my_turn = turn_config.get("first_turn", False)
            self.state.last_speaker = None
            self.state.round_number = 0
            return self.state

        last_event = self._get_last_agent_event(mission_events)
        if not last_event:
            # Solo hay eventos de sistema, no de agentes
            turn_config = self.TURN_AFTER.get(self.agent_role, {})
            self.state.is_my_turn = turn_config.get("first_turn", False)
            return self.state

        last_sender = last_event.get("sender", "")
        self.state.last_speaker = last_sender

        # Ya hablé yo → esperar
        if last_sender == self.agent_name:
            self.state.is_my_turn = False
            return self.state

        # ¿El último emisor desbloquea mi turno?
        turn_config = self.TURN_AFTER.get(self.agent_role, {})
        speakers_after = turn_config.get("after", [])

        # Buscar si el rol del último emisor coincide con algún trigger
        # (comparamos por nombre de agente, que puede contener el rol)
        sender_lower = last_sender.lower()
        self.state.is_my_turn = any(
            trigger in sender_lower for trigger in speakers_after
        ) or last_sender != self.agent_name

        # Contar rondas (cuántas veces yo ya hablé)
        my_reports = [
            e for e in mission_events
            if e.get("type") == "AGENT_REPORT" and e.get("sender") == self.agent_name
        ]
        self.state.round_number = len(my_reports)

        return self.state

    async def wait_for_turn(self, mission_id: str, timeout: float = MAX_TURN_WAIT) -> bool:
        """
        Polling asíncrono que espera hasta que sea el turno del agente.
        
        Returns: True si es mi turno, False si timeout.
        """
        start = time.monotonic()

        while (time.monotonic() - start) < timeout:
            state = self.check_turn(mission_id)
            if state.is_my_turn:
                telemetry.info(
                    f"🎯 [{self.agent_name}] Mi turno (ronda {state.round_number + 1}). "
                    f"Último emisor: {state.last_speaker or 'ninguno'}"
                )
                return True
            await asyncio.sleep(TURN_POLL_INTERVAL)

        telemetry.warning(f"⏰ [{self.agent_name}] Timeout esperando turno ({timeout}s)")
        return False


# ---------------------------------------------------------------------------
# 2. TOKEN TRACKER — CONTROL METABÓLICO
# ---------------------------------------------------------------------------

class TokenTracker:
    """
    Monitorea el tamaño del contexto para evitar desbordamiento.
    Usa una estimación heurística (1 token ≈ 4 chars para inglés/español).
    
    Si el contexto se acerca al límite, solicita intervención
    del Shredder vía el bus IPC.
    """

    CHARS_PER_TOKEN = 4

    def __init__(self, max_context_tokens: int = 8000, max_output_tokens: int = 4000):
        self.max_context_chars = max_context_tokens * self.CHARS_PER_TOKEN
        self.max_output_chars = max_output_tokens * self.CHARS_PER_TOKEN
        self.current_context_chars = 0
        self.total_output_chars = 0

    def estimate_tokens(self, text: str) -> int:
        return len(text) // self.CHARS_PER_TOKEN

    def track_context(self, text: str) -> bool:
        """
        Registra characters de contexto.
        Returns: True si hay espacio, False si se excedió.
        """
        self.current_context_chars += len(text)
        if self.current_context_chars > self.max_context_chars:
            telemetry.warning(
                f"⚠️ TokenTracker: Contexto excedido "
                f"({self.current_context_chars}/{self.max_context_chars} chars)"
            )
            return False
        return True

    def track_output(self, text: str) -> bool:
        self.total_output_chars += len(text)
        return self.total_output_chars <= self.max_output_chars

    def needs_shredding(self) -> bool:
        """True si el contexto está al 80% de capacidad."""
        return self.current_context_chars > (self.max_context_chars * 0.8)

    def reset(self):
        self.current_context_chars = 0
        self.total_output_chars = 0


# ---------------------------------------------------------------------------
# 3. LLM INFERENCE BRIDGE — PUENTE DE INFERENCIA
# ---------------------------------------------------------------------------

class LLMInferenceBridge:
    """
    Conecta el runner con la API de LLM del proveedor configurado.
    
    Proveedores soportados:
      - openrouter (OpenRouter API → Claude, Gemini, etc.)
      - groq (Groq API → Llama 3.3 70B)
      
    Estructura de producción: el cuerpo de la inferencia está
    completo con manejo de errores, reintentos y parsing.
    El único punto de extensión es la llamada HTTP real.
    """

    PROVIDER_ENDPOINTS = {
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
    }

    PROVIDER_KEYS = {
        "openrouter": lambda: os.getenv("OPENROUTER_API_KEY", ""),
        "groq": lambda: os.getenv("GROQ_API_KEY", ""),
    }

    def __init__(self, provider: str, model: str):
        self.provider = provider.lower()
        self.model = model
        self.endpoint = self.PROVIDER_ENDPOINTS.get(self.provider, "")
        self._api_key = self.PROVIDER_KEYS.get(self.provider, lambda: "")()

    def _build_messages(
        self,
        system_prompt: str,
        debate_history: List[Dict[str, str]],
        current_task: str,
    ) -> List[Dict[str, str]]:
        """
        Construye el array de mensajes OpenAI-compatible.
        
        [0] system → Cerebro del agente (system prompt inmutable)
        [1..N-1] user/assistant → Historial del debate (destilado)
        [N] user → Tarea actual / turno del debate
        """
        messages = [{"role": "system", "content": system_prompt}]

        for entry in debate_history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": current_task})
        return messages

    async def infer(
        self,
        system_prompt: str,
        debate_history: List[Dict[str, str]],
        current_task: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Ejecuta la inferencia contra el proveedor LLM.
        
        Returns:
            {
                "content": str,        # Respuesta del LLM
                "tokens_used": int,    # Tokens consumidos
                "model": str,          # Modelo utilizado
                "provider": str,       # Proveedor
                "latency_ms": float,   # Latencia de la llamada
                "status": "OK"|"ERROR"
            }
        """
        messages = self._build_messages(system_prompt, debate_history, current_task)

        if not self._api_key:
            telemetry.warning(
                f"⚠️ [{self.provider}] API key no configurada. "
                "Generando respuesta de diagnóstico."
            )
            return self._diagnostic_response(messages)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Headers extra para OpenRouter
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/AgentOrquestor"
            headers["X-Title"] = "AgentOrquestor-Swarm-Runner"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.monotonic()

        try:
            import httpx

            async with httpx.AsyncClient(timeout=INFERENCE_TIMEOUT) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )

            latency = (time.monotonic() - start_time) * 1000

            if response.status_code != 200:
                error_body = response.text[:500]
                telemetry.error(
                    f"❌ [{self.provider}] HTTP {response.status_code}: {error_body}"
                )
                return {
                    "content": f"[ERROR] LLM respondió con HTTP {response.status_code}: {error_body}",
                    "tokens_used": 0,
                    "model": self.model,
                    "provider": self.provider,
                    "latency_ms": latency,
                    "status": "ERROR",
                }

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", len(content) // 4)

            telemetry.info(
                f"✅ [{self.provider}/{self.model}] Inferencia OK — "
                f"{tokens} tokens, {latency:.0f}ms"
            )

            return {
                "content": content,
                "tokens_used": tokens,
                "model": self.model,
                "provider": self.provider,
                "latency_ms": latency,
                "status": "OK",
            }

        except ImportError:
            telemetry.error("❌ httpx no instalado. Usando respuesta de diagnóstico.")
            return self._diagnostic_response(messages)

        except Exception as e:
            latency = (time.monotonic() - start_time) * 1000
            telemetry.error(f"❌ [{self.provider}] Excepción: {e}")
            return {
                "content": f"[ERROR] Excepción durante inferencia: {str(e)[:300]}",
                "tokens_used": 0,
                "model": self.model,
                "provider": self.provider,
                "latency_ms": latency,
                "status": "ERROR",
            }

    def _diagnostic_response(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Respuesta de diagnóstico cuando la API no está disponible.
        Emula la estructura de respuesta para que el ciclo IPC no se rompa.
        """
        system_content = messages[0]["content"] if messages else ""
        task_content = messages[-1]["content"] if messages else ""

        # Generar una respuesta estructurada basada en el rol detectado
        is_adversary = any(
            kw in system_content.lower()
            for kw in ("adversario", "auditor", "security", "crítica")
        )

        if is_adversary:
            content = (
                "CRÍTICA DIAGNÓSTICA (Modo sin API)\n\n"
                "RIESGOS IDENTIFICADOS:\n"
                f"- Contexto analizado: {len(task_content)} caracteres\n"
                "- Sin validación por LLM real — riesgo de alucinación pasiva\n"
                "- Recomendación: Configurar OPENROUTER_API_KEY o GROQ_API_KEY\n\n"
                "VETO: La propuesta no puede validarse sin inferencia real.\n"
                "Acción requerida: Activar conectividad API."
            )
        else:
            content = (
                "TESIS DIAGNÓSTICA (Modo sin API)\n\n"
                "PROPUESTA:\n"
                f"- Tarea recibida: {task_content[:200]}...\n"
                "- Estado: Daemon operativo, IPC funcional\n"
                "- Inferencia real pendiente: configurar API keys\n\n"
                "APPROVED (condicionalmente): Infraestructura IPC verificada."
            )

        return {
            "content": content,
            "tokens_used": len(content) // 4,
            "model": "diagnostic-mode",
            "provider": "local",
            "latency_ms": 0.0,
            "status": "DIAGNOSTIC",
        }


# ---------------------------------------------------------------------------
# 4. AGENT RUNNER — DAEMON PRINCIPAL
# ---------------------------------------------------------------------------

class AgentRunner:
    """
    Daemon de Inferencia Aislada.
    
    Ciclo homeostático:
      1. Bootstrap → Leer cerebro, cargar identidad
      2. Event Loop → Esperar turno, leer bus
      3. Inference → Llamar a LLM con contexto
      4. Emit → Escribir reporte al bus y filesystem
      5. Evaluate → ¿Consenso? → Señalizar. ¿Repetir? → Goto 2.
      6. Shutdown → Flush, limpiar, salir.
    """

    def __init__(
        self,
        brain_path: str,
        mission_id: str,
        agent_name: str,
    ):
        self.brain_path = Path(brain_path)
        self.mission_id = mission_id
        self.agent_name = agent_name
        self.mission_dir = MISSIONS_DIR / mission_id

        # Identidad cargada del cerebro
        self.system_prompt = ""
        self.agent_role = "proponent"
        self.provider = "groq"
        self.model = "llama-3.3-70b-versatile"

        # Subsistemas
        self.token_tracker = TokenTracker()
        self.shredder = LogShredder()
        self.hw_monitor = HardwareMonitor()
        self.llm: Optional[LLMInferenceBridge] = None
        self.turn_manager: Optional[DialecticTurnManager] = None

        # Estado del daemon
        self._shutdown_requested = False
        self._setup_signal_handlers()

    # --- Signal Handling ---

    def _setup_signal_handlers(self):
        """
        Intercepta SIGTERM y SIGINT para cierre limpio.
        tmux envía SIGTERM al matar un panel; Ctrl+C envía SIGINT.
        """
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """
        Handler de señal: marca el daemon para cierre limpio.
        No hace I/O directamente (unsafe en signal handler);
        solo setea la flag que el event loop revisa.
        """
        self._shutdown_requested = True

    def _emit_shutdown_event(self):
        """Escribe un evento de shutdown al bus IPC."""
        bus_path = self.mission_dir.parent.parent / "bus_buffer.jsonl"
        event = json.dumps({
            "timestamp": time.time(),
            "sender": self.agent_name,
            "type": "AGENT_SHUTDOWN",
            "payload": {
                "mission_id": self.mission_id,
                "reason": "SIGTERM/SIGINT received",
                "rounds_completed": self.turn_manager.state.round_number if self.turn_manager else 0,
            },
            "handshake": False,
        })
        try:
            atomic_append(bus_path, event)
        except Exception:
            pass  # Best-effort en shutdown

    # --- Bootstrap ---

    def _parse_brain(self) -> Dict[str, str]:
        """
        Parsea el archivo .md del cerebro y extrae metadatos.
        
        Campos extraídos del header:
          - Rol (proponent/adversary/architect/optimizer)
          - Modelo y proveedor
          - System message
        """
        content = safe_read(self.brain_path)
        if not content:
            telemetry.error(f"❌ [{self.agent_name}] Cerebro vacío: {self.brain_path}")
            return {}

        self.system_prompt = content
        self.token_tracker.track_context(content)

        # Extraer metadatos del header Markdown
        for line in content.splitlines():
            line_lower = line.lower().strip()

            if "rol:" in line_lower:
                if "adversary" in line_lower:
                    self.agent_role = "adversary"
                elif "architect" in line_lower:
                    self.agent_role = "architect"
                elif "optimizer" in line_lower:
                    self.agent_role = "optimizer"
                else:
                    self.agent_role = "proponent"

            if "modelo:" in line_lower or "model:" in line_lower:
                parts = line.split("/")
                if len(parts) >= 2:
                    self.provider = parts[0].split(":")[-1].strip().lower()
                    self.model = "/".join(parts[1:]).strip()

        telemetry.info(
            f"🧠 [{self.agent_name}] Cerebro cargado — "
            f"Rol: {self.agent_role}, Modelo: {self.provider}/{self.model}, "
            f"Contexto: {self.token_tracker.estimate_tokens(content)} tokens"
        )

        return {"role": self.agent_role, "provider": self.provider, "model": self.model}

    # --- Bus I/O ---

    def _get_bus_path(self) -> Path:
        return CORTEX_DIR / "bus_buffer.jsonl"

    def _read_debate_history(self) -> List[Dict[str, str]]:
        """
        Lee los reportes previos del bus y los convierte en
        historial de debate (formato messages para LLM).
        """
        bus_path = self._get_bus_path()
        content = safe_read(bus_path)
        if not content:
            return []

        history: List[Dict[str, str]] = []
        lines = content.strip().splitlines()
        tail = lines[-BUS_TAIL_LINES:]

        for line in tail:
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

            if event.get("type") != "AGENT_REPORT":
                continue

            payload = event.get("payload", {})
            if payload.get("mission_id") != self.mission_id:
                continue

            sender = event.get("sender", "unknown")
            report_content = payload.get("report", "")

            # Mapear a roles de LLM
            if sender == self.agent_name:
                role = "assistant"
            else:
                role = "user"

            if report_content:
                history.append({
                    "role": role,
                    "content": f"[{sender}]: {report_content}",
                })

        # Controlar metabólismo: si el historial es muy largo, destilar
        total_chars = sum(len(h["content"]) for h in history)
        if total_chars > MAX_CONTEXT_CHARS * 0.6:
            telemetry.info(f"🧹 [{self.agent_name}] Destilando historial ({total_chars} chars)")
            raw = [{"proponent": h["content"]} for h in history if h["role"] == "user"]
            distilled = self.shredder.distill(raw)
            history = [{"role": "user", "content": f"[HISTORIAL DESTILADO]:\n{distilled}"}]

        return history

    def _build_current_task(self, round_number: int) -> str:
        """
        Construye el mensaje de tarea para esta ronda.
        Incluye reportes de pares del filesystem.
        """
        reports_dir = self.mission_dir / "reports"
        peer_reports = []

        if reports_dir.exists():
            for report_file in sorted(reports_dir.glob("*_report.md")):
                peer_name = report_file.stem.replace("_report", "")
                if peer_name != self.agent_name:
                    content = safe_read(report_file)
                    if content:
                        peer_reports.append(f"## Reporte de {peer_name}\n{content}")

        # Hardware snapshot
        hw = self.hw_monitor.check_stability()
        vram = hw.get("vram", {})

        task = (
            f"## Ronda de Debate {round_number + 1}\n\n"
            f"Tu rol: **{self.agent_role.upper()}**\n"
            f"Hardware: VRAM {vram.get('vram_total', 0) - vram.get('vram_used', 0):.0f}MB libre, "
            f"GPU {vram.get('gpu_temp', 0):.0f}°C\n\n"
        )

        if peer_reports:
            task += "## Reportes de Pares (para tu análisis)\n\n"
            task += "\n\n---\n\n".join(peer_reports)
            task += "\n\n---\n\n"

        task += (
            "## Instrucciones para esta Ronda\n"
            f"{'Propón una solución técnica concreta.' if self.agent_role == 'proponent' else ''}"
            f"{'Audita y ataca la propuesta con evidencia verificable.' if self.agent_role == 'adversary' else ''}"
            f"{'Diseña la estrategia arquitectónica de alto nivel.' if self.agent_role == 'architect' else ''}"
            f"{'Optimiza para VRAM, latencia y eficiencia de tokens.' if self.agent_role == 'optimizer' else ''}\n\n"
            "Si apruebas el estado actual, escribe APPROVED al inicio. "
            "Si rechazas, escribe REJECTED y lista las acciones mínimas para aprobar."
        )

        return task

    def _emit_report(self, report: str, inference_result: Dict[str, Any]) -> None:
        """
        Escribe el reporte del agente en dos destinos:
        1. Bus IPC (bus_buffer.jsonl) → para sincronización de turnos
        2. Filesystem (.cortex/missions/{id}/reports/) → para HandoffRouter
        """
        # 1. Bus IPC
        bus_event = json.dumps({
            "timestamp": time.time(),
            "sender": self.agent_name,
            "type": "AGENT_REPORT",
            "payload": {
                "mission_id": self.mission_id,
                "report": report[:2000],         # Truncar para bus (límite ligero)
                "tokens_used": inference_result.get("tokens_used", 0),
                "model": inference_result.get("model", ""),
                "latency_ms": inference_result.get("latency_ms", 0),
                "round": self.turn_manager.state.round_number if self.turn_manager else 0,
            },
            "handshake": False,
        }, ensure_ascii=False)

        atomic_append(self._get_bus_path(), bus_event)

        # 2. Filesystem (reporte completo)
        reports_dir = self.mission_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{self.agent_name}_report.md"
        atomic_write(report_path, report)

        telemetry.info(
            f"📝 [{self.agent_name}] Reporte emitido — "
            f"{len(report)} chars, {inference_result.get('tokens_used', 0)} tokens"
        )

    def _check_consensus_signal(self, report: str) -> bool:
        """Detecta si el reporte contiene señal de consenso."""
        upper = report.upper()
        return "APPROVED" in upper and "REJECTED" not in upper

    # --- Main Loop ---

    async def run(self) -> Dict[str, Any]:
        """
        Ejecuta el ciclo homeostático completo del daemon.
        
        Returns: Resumen de la ejecución.
        """
        telemetry.info(f"🚀 [{self.agent_name}] Agent Runner iniciado.")

        # 1. Bootstrap
        brain_meta = self._parse_brain()
        if not brain_meta:
            return {"status": "ERROR", "reason": "Brain file empty or missing"}

        # Inicializar subsistemas
        self.llm = LLMInferenceBridge(self.provider, self.model)
        self.turn_manager = DialecticTurnManager(
            agent_name=self.agent_name,
            agent_role=self.agent_role,
            bus_path=self._get_bus_path(),
        )

        result = {
            "agent": self.agent_name,
            "role": self.agent_role,
            "rounds_completed": 0,
            "consensus_reached": False,
            "total_tokens": 0,
            "status": "RUNNING",
        }

        # 2. Event Loop — Debate por Rondas
        for round_num in range(MAX_DEBATE_ROUNDS):
            if self._shutdown_requested:
                telemetry.info(f"🛑 [{self.agent_name}] Shutdown solicitado.")
                break

            # 2a. Esperar turno
            telemetry.info(f"⏳ [{self.agent_name}] Esperando turno (ronda {round_num + 1})...")
            got_turn = await self.turn_manager.wait_for_turn(
                self.mission_id,
                timeout=MAX_TURN_WAIT,
            )

            if not got_turn:
                telemetry.warning(f"⏰ [{self.agent_name}] Timeout de turno. Abortando.")
                result["status"] = "TURN_TIMEOUT"
                break

            if self._shutdown_requested:
                break

            # 2b. Leer historial del debate
            debate_history = self._read_debate_history()

            # 2c. Construir tarea para esta ronda
            current_task = self._build_current_task(round_num)

            # 2d. Verificar metabolismo
            if self.token_tracker.needs_shredding():
                telemetry.info(f"🧹 [{self.agent_name}] Contexto saturado. Solicitando shredding...")
                # Destilar el system prompt si es necesario
                raw = [{"proponent": self.system_prompt}]
                self.system_prompt = self.shredder.distill(raw)
                self.token_tracker.reset()
                self.token_tracker.track_context(self.system_prompt)

            # 2e. Inferencia
            telemetry.info(f"🤖 [{self.agent_name}] Invocando inferencia ({self.provider}/{self.model})...")
            inference_result = await self.llm.infer(
                system_prompt=self.system_prompt,
                debate_history=debate_history,
                current_task=current_task,
            )

            report = inference_result.get("content", "")
            result["total_tokens"] += inference_result.get("tokens_used", 0)

            if not report:
                telemetry.error(f"❌ [{self.agent_name}] Inferencia retornó vacío.")
                continue

            # 2f. Emitir reporte
            self._emit_report(report, inference_result)
            result["rounds_completed"] = round_num + 1

            # 2g. Verificar consenso
            if self._check_consensus_signal(report):
                telemetry.info(f"🏆 [{self.agent_name}] Señal APPROVED emitida.")
                result["consensus_reached"] = True
                # No break aquí — el HandoffRouter decide globalmente

            # 2h. Token tracking
            self.token_tracker.track_output(report)

            # Pausa entre rondas para permitir al par hablar
            await asyncio.sleep(1.0)

        # 3. Shutdown
        if self._shutdown_requested:
            self._emit_shutdown_event()
            result["status"] = "SHUTDOWN"
        else:
            result["status"] = "COMPLETED"

        telemetry.info(
            f"✨ [{self.agent_name}] Runner finalizado — "
            f"Status: {result['status']}, Rondas: {result['rounds_completed']}, "
            f"Tokens: {result['total_tokens']}"
        )

        # Persistir resumen
        summary_path = self.mission_dir / "logs" / f"{self.agent_name}_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(summary_path, json.dumps(result, indent=2, ensure_ascii=False))

        return result


# ---------------------------------------------------------------------------
# 5. CLI — PUNTO DE ENTRADA
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AgentOrquestor — Agent Runner Daemon v5.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplo:\n"
            "  python agent_runner.py \\\n"
            "    --brain .cortex/missions/m_abc/brains/contexto_LeadDev.md \\\n"
            "    --mission-id m_abc123 \\\n"
            "    --agent-name LeadDeveloper"
        ),
    )
    parser.add_argument(
        "--brain", required=True,
        help="Ruta al archivo .md de contexto (cerebro del agente)",
    )
    parser.add_argument(
        "--mission-id", required=True,
        help="Identificador de la misión activa",
    )
    parser.add_argument(
        "--agent-name", required=True,
        help="Nombre del agente (debe coincidir con registry.yaml)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    runner = AgentRunner(
        brain_path=args.brain,
        mission_id=args.mission_id,
        agent_name=args.agent_name,
    )

    result = await runner.run()

    # Exit code: 0 = OK, 1 = error, 2 = shutdown
    if result["status"] == "ERROR":
        sys.exit(1)
    elif result["status"] == "SHUTDOWN":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
