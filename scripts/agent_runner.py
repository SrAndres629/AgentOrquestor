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
import traceback
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
from core.mcp_proxy import mcp_proxy as global_mcp_proxy
from core.metabolic_governor import mcu as global_mcu
from core.neural_trace import (
    initialize_tracer, 
    get_tracer, 
    NeuralSpan, 
    extract_trace_context
)


# ---------------------------------------------------------------------------
# 0. CONSTANTES Y CONFIGURACIÓN
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Límites metabólicos por agente
MAX_CONTEXT_CHARS = 32000          # ~8000 tokens aprox
MAX_OUTPUT_CHARS = 16000           # ~4000 tokens aprox
BUS_TAIL_LINES = 20               # Últimas N líneas del bus a considerar (optimizando tokens)
TURN_POLL_INTERVAL = 5.0           # Segundos entre polls de turno (mitigando 429)
MAX_TURN_WAIT = 120.0              # Timeout máximo esperando turno
INFERENCE_TIMEOUT = 60.0           # Timeout de llamada al LLM
MAX_DEBATE_ROUNDS = 3              # Rondas máximas de debate interno
MAX_TOOL_ROUNDS = 3                # Máx iteraciones tool_call por turno


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
    trace_context: Optional[Any] = None


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

    # Los ayudantes _read_bus_tail y _get_mission_events han sido eliminados
    # ya que TurnManager ahora usa bus.read_mailbox activamente.

    def check_turn(self, mission_id: str) -> TurnState:
        """
        Determina si es el turno de este agente usando Mailboxes.
        """
        from core.event_bus import bus
        
        # 1. Leer mi propio buzón para ver mi última acción
        my_events = bus.read_mailbox(self.agent_name, limit=5)
        my_mission_events = [e for e in my_events if e.get("payload", {}).get("mission_id") == mission_id]
        my_last_report = next((e for e in reversed(my_mission_events) if e.get("type") == "AGENT_REPORT"), None)
        
        # 2. Identificar de quién dependo
        turn_config = self.TURN_AFTER.get(self.agent_role, {})
        speakers_after = turn_config.get("after", [])
        is_first = turn_config.get("first_turn", False)
        
        # Si soy el primero y no he dicho nada: TURNO MÍO
        if not my_last_report and is_first:
            # Verificar si alguien más ya habló (pudo haber empezado otro)
            # Para estar seguros, checkeamos todos los 'after'
            someone_spoke = False
            for peer in speakers_after:
                peer_events = bus.read_mailbox(peer, limit=2)
                if any(e.get("payload", {}).get("mission_id") == mission_id for e in peer_events):
                    someone_spoke = True
                    break
            
            if not someone_spoke:
                self.state.is_my_turn = True
                self.state.round_number = 0
                self.state.trace_context = None # No hay evento previo para extraer contexto
                return self.state

        # 3. Leer buzones de los que 'desbloquean' mi turno
        peer_reports = []
        for peer in speakers_after:
            peer_events = bus.read_mailbox(peer, limit=5)
            peer_mission_events = [e for e in peer_events if e.get("payload", {}).get("mission_id") == mission_id]
            peer_last = next((e for e in reversed(peer_mission_events) if e.get("type") == "AGENT_REPORT"), None)
            if peer_last:
                peer_reports.append(peer_last)
        
        if not peer_reports:
            # Si no hay reportes de mis triggers, y no soy el primero: ESPERAR
            self.state.is_my_turn = is_first and not my_last_report
            self.state.trace_context = None # No hay evento previo para extraer contexto
            return self.state

        # Encontrar el reporte de par más reciente
        peer_reports.sort(key=lambda x: x.get("timestamp", 0))
        last_peer_report = peer_reports[-1]
        
        self.state.last_speaker = last_peer_report.get("sender")
        
        # Lógica de turno:
        # Si el reporte de par es más reciente que el mío (o no tengo ninguno) -> MI TURNO
        if not my_last_report:
            self.state.is_my_turn = True
            self.state.trace_context = extract_trace_context(last_peer_report)
        else:
            self.state.is_my_turn = last_peer_report.get("timestamp", 0) > my_last_report.get("timestamp", 0)
            if self.state.is_my_turn:
                self.state.trace_context = extract_trace_context(last_peer_report)
            else:
                self.state.trace_context = None # No es mi turno, no hay contexto relevante para iniciar
            
        # Contar rondas
        self.state.round_number = len([e for e in my_mission_events if e.get("type") == "AGENT_REPORT"])
        
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
    Soporta Function Calling / Tool Use nativo de Groq y OpenRouter.
    
    Ciclo de inferencia con herramientas:
      1. Enviar mensajes + definiciones de tools al LLM
      2. Si el LLM responde con tool_calls → ejecutar vía MCPProxy
      3. Inyectar resultados como mensajes "tool" y re-invocar LLM
      4. Repetir hasta que el LLM emita texto final (o MAX_TOOL_ROUNDS)
    
    Proveedores soportados:
      - openrouter (OpenRouter API → Claude, Gemini, etc.)
      - groq (Groq API → Llama 3.3 70B)
    """

    PROVIDER_ENDPOINTS = {
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
    }

    PROVIDER_KEYS = {
        "openrouter": lambda: os.getenv("OPENROUTER_API_KEY", ""),
        "groq": lambda: os.getenv("GROQ_API_KEY", ""),
    }

    def __init__(self, provider: str, model: str, mcp_proxy=None):
        self.provider = provider.lower()
        self.model = model
        self.endpoint = self.PROVIDER_ENDPOINTS.get(self.provider, "")
        self._api_key = self.PROVIDER_KEYS.get(self.provider, lambda: "")()
        self.mcp = mcp_proxy or global_mcp_proxy
        self._tool_calls_executed: List[Dict[str, Any]] = []

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

    def _build_tool_definitions(self, allowed_tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Convierte el catálogo de MCPProxy a formato OpenAI function-calling.
        Filtra por herramientas permitidas en el cerebro del agente.
        """
        catalog = self.mcp.get_available_tools()
        definitions = []

        for tool in catalog:
            name = tool["name"]
            
            # Herramientas de soberanía siempre visibles
            is_sovereign = name == "register_new_tool"
            
            if not is_sovereign and allowed_tools and name not in allowed_tools:
                continue
            
            if name == "register_new_tool":
                definitions.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool["desc"],
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "agent_name": {
                                    "type": "string",
                                    "description": "Nombre del agente al que se le asignará la herramienta (ej. LeadDeveloper)"
                                },
                                "tool_name": {
                                    "type": "string",
                                    "description": "Nombre técnico de la nueva herramienta/skill"
                                }
                            },
                            "required": ["agent_name", "tool_name"],
                        },
                    },
                })
                continue

            definitions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("desc", f"Herramienta MCP: {name}"),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Acción específica a ejecutar"
                            },
                            "target": {
                                "type": "string",
                                "description": "Objetivo o ruta de la acción"
                            },
                            "params": {
                                "type": "object",
                                "description": "Parámetros adicionales"
                            },
                        },
                        "required": ["action"],
                    },
                },
            })

        return definitions

    async def _execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta cada tool_call vía MCPProxy y retorna los resultados
        como mensajes "tool" para re-inyectar al LLM.
        """
        results = []

        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_name = fn.get("name", "unknown")
            tool_call_id = tc.get("id", f"tc_{int(time.time())}")

            # Parsear argumentos (LLM los envía como JSON string)
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                args = {}

            telemetry.info(f"🔧 Tool Call: {tool_name}({json.dumps(args, ensure_ascii=False)[:200]})")

            try:
                mcp_result = await self.mcp.call_tool(tool_name, args)
            except Exception as e:
                mcp_result = {"status": "ERROR", "message": str(e)[:300]}

            result_text = json.dumps(mcp_result, ensure_ascii=False)
            
            # --- PARCHE 3: Truncamiento Defensivo ---
            if len(result_text) > 4000:
                result_text = result_text[:4000] + "... [OUTPUT_TRUNCATED_BY_SYSTEM]"
            
            telemetry.info(f"🔧 Tool Result [{tool_name}]: {result_text[:200]}")

            # Registrar para traceability
            self._tool_calls_executed.append({
                "tool": tool_name,
                "args": args,
                "result": mcp_result,
                "timestamp": time.time(),
            })

            # Mensaje de resultado para el LLM (formato OpenAI tool response)
            results.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_text,
            })

        return results

    async def _raw_api_call(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ejecuta una llamada HTTP al endpoint del LLM con Resiliencia Metabólica (Backoff).
        Implementa reintentos exponenciales para errores 429 (Rate Limit).
        """
        import httpx
        import random
        
        max_retries = 5
        base_delay = 2.0  # s
        
        tracer = get_tracer("llm_bridge")
        with NeuralSpan.llm_span(tracer, "LLM Inference", self.model, str(payload.get("messages", ""))[:1000]):
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=INFERENCE_TIMEOUT) as client:
                        response = await client.post(
                            self.endpoint,
                            headers=headers,
                            json=payload,
                        )

                    if response.status_code == 200:
                        return response.json()
                    
                    if response.status_code == 429:
                        delay = (base_delay * (2 ** attempt)) + (random.random() * 2.0)
                        telemetry.warning(
                            f"⏳ [{self.provider}] Rate Limit (429). Reintentando en {delay:.1f}s... "
                            f"(Intento {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    # Otros errores HTTP
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {response.text[:500]}"
                    )

                except httpx.RequestError as e:
                    if attempt == max_retries - 1:
                        break
                    delay = base_delay * (attempt + 1)
                    telemetry.error(f"🌐 Error de red: {e}. Reintentando en {delay}s...")
                    await asyncio.sleep(delay)

            # Si llegamos aquí, es que agotamos los reintentos
            telemetry.error(f"💀 [{self.provider}] ASFIXIA METABÓLICA: Max retries exceeded.")
            
            # Reportar fallo fatal al bus antes de morir
            fatal_msg = (
                f"[NETWORK_FATAL_ERROR] El agente ha muerto por asfixia del proveedor ({self.provider}). "
                f"Rate limit persistente tras {max_retries} reintentos."
            )
            
            # Intentar escribir reporte final
            try:
                from core.event_bus import bus
                
                report_payload = {
                    "mission_id": self.mission_id,
                    "report": fatal_msg,
                    "status": "FATAL",
                    "round": 99 # Ronda de salida
                }
                bus.publish("AGENT_REPORT", report_payload, sender=self.agent_name)
            except:
                pass
                
            raise RuntimeError("Max retries reached for LLM API.")
            
        import sys
        sys.exit(1)

    async def infer(
        self,
        system_prompt: str,
        debate_history: List[Dict[str, str]],
        current_task: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        allowed_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta inferencia con soporte completo de Function Calling.
        
        Ciclo:
          1. Enviar mensajes + tools al LLM
          2. Si tool_calls → ejecutar → re-enviar con resultados
          3. Repetir hasta texto final o MAX_TOOL_ROUNDS
        
        Returns:
            {
                "content": str,
                "tokens_used": int,
                "model": str,
                "provider": str,
                "latency_ms": float,
                "status": "OK"|"ERROR"|"DIAGNOSTIC",
                "tool_calls": List[Dict],  # Herramientas ejecutadas
            }
        """
        messages = self._build_messages(system_prompt, debate_history, current_task)
        self._tool_calls_executed = []

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
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/AgentOrquestor"
            headers["X-Title"] = "AgentOrquestor-Swarm-Runner"

        # Construir definiciones de herramientas
        tool_defs = self._build_tool_definitions(allowed_tools)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tool_defs:
            payload["tools"] = tool_defs
            payload["tool_choice"] = "auto"

        start_time = time.monotonic()
        total_tokens = 0

        try:
            # --- Bucle de Tool Calling ---
            for tool_round in range(MAX_TOOL_ROUNDS + 1):
                data = await self._raw_api_call(headers, payload)
                usage = data.get("usage", {})
                total_tokens += usage.get("total_tokens", 0)

                choice = data["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason", "stop")

                # ¿El LLM solicita tool_calls?
                tool_calls = message.get("tool_calls")

                if tool_calls and tool_round < MAX_TOOL_ROUNDS:
                    telemetry.info(
                        f"🔧 [{self.provider}] {len(tool_calls)} tool_calls detectados "
                        f"(ronda {tool_round + 1}/{MAX_TOOL_ROUNDS})"
                    )

                    # Agregar el mensaje del asistente con tool_calls
                    messages.append(message)

                    # Ejecutar herramientas y obtener resultados (Titanium Funnel Applied - Guide 04)
                    tool_results = await self._execute_tool_calls(tool_calls)
                    
                    MAX_TOOL_CHARS = 4000
                    for tr in tool_results:
                        content = tr.get("content", "")
                        if len(content) > MAX_TOOL_CHARS:
                            tr["content"] = content[:MAX_TOOL_CHARS] + f"\n... [TRUNCADO: Salida superaba los {MAX_TOOL_CHARS} chars. Refina tu consulta.]"

                    messages.extend(tool_results)

                    # Actualizar payload para la siguiente iteración
                    payload["messages"] = messages
                    continue

                # Respuesta final (texto)
                content = message.get("content", "")
                if not content and tool_calls:
                    # Último round fue tool_call sin texto → forzar cierre
                    content = (
                        f"[Auto-síntesis] Herramientas ejecutadas: "
                        + ", ".join(tc["function"]["name"] for tc in tool_calls)
                    )

                latency = (time.monotonic() - start_time) * 1000

                telemetry.info(
                    f"✅ [{self.provider}/{self.model}] Inferencia OK — "
                    f"{total_tokens} tokens, {latency:.0f}ms, "
                    f"{len(self._tool_calls_executed)} tools ejecutados"
                )

                return {
                    "content": content,
                    "tokens_used": total_tokens,
                    "model": self.model,
                    "provider": self.provider,
                    "latency_ms": latency,
                    "status": "OK",
                    "tool_calls": self._tool_calls_executed,
                }

            # Si agotamos MAX_TOOL_ROUNDS sin texto final
            latency = (time.monotonic() - start_time) * 1000
            telemetry.warning(f"⚠️ [{self.provider}] MAX_TOOL_ROUNDS agotados sin texto final.")
            return {
                "content": "[WARN] Máximo de rondas de herramientas alcanzado sin síntesis final.",
                "tokens_used": total_tokens,
                "model": self.model,
                "provider": self.provider,
                "latency_ms": latency,
                "status": "OK",
                "tool_calls": self._tool_calls_executed,
            }

        except ImportError:
            telemetry.error("❌ httpx no instalado. Usando respuesta de diagnóstico.")
            return self._diagnostic_response(messages)

        except Exception as e:
            latency = (time.monotonic() - start_time) * 1000
            telemetry.error(f"❌ [{self.provider}] Excepción: {e}")
            return {
                "content": f"[ERROR] Excepción durante inferencia: {str(e)[:300]}",
                "tokens_used": total_tokens,
                "model": self.model,
                "provider": self.provider,
                "latency_ms": latency,
                "status": "ERROR",
                "tool_calls": self._tool_calls_executed,
            }

    def _diagnostic_response(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Respuesta de diagnóstico cuando la API no está disponible.
        Emula la estructura de respuesta para que el ciclo IPC no se rompa.
        """
        system_content = messages[0]["content"] if messages else ""
        task_content = messages[-1]["content"] if messages else ""

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
            "tool_calls": [],
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
        self.allowed_tools: List[str] = []

        # Subsistemas
        self.token_tracker = TokenTracker()
        self.shredder = LogShredder()
        self.hw_monitor = HardwareMonitor()
        self.mcu = global_mcu
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
        """Emite evento de apagado al buzón."""
        from core.event_bus import bus
        try:
            bus.publish("AGENT_SHUTDOWN", {"mission_id": self.mission_id}, sender=self.agent_name)
            telemetry.info(f"🛑 [{self.agent_name}] Evento SHUTDOWN emitido.")
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

            if "herramientas:" in line_lower or "tools:" in line_lower:
                tools_line = line.split(":")[-1].strip()
                # Parsear lista separada por comas dentro o fuera de [ ]
                tools_line = tools_line.strip("[]")
                self.allowed_tools = [t.strip().strip("`") for t in tools_line.split(",") if t.strip()]

        telemetry.info(
            f"🧠 [{self.agent_name}] Cerebro cargado — "
            f"Rol: {self.agent_role}, Modelo: {self.provider}/{self.model}, "
            f"Tools: {self.allowed_tools}, "
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

    def _emit_report(self, report: str, inference_result: Dict[str, Any]):
        """
        Emite el reporte al buzón atómico y al filesystem.
        """
        from core.event_bus import bus
        
        # 1. Mailbox IPC
        mcu_health = self.mcu.check_health(self.mission_id)
        payload = {
            "mission_id": self.mission_id,
            "report": report[:2000],         # Truncar para bus (límite ligero)
            "tokens_used": inference_result.get("tokens_used", 0),
            "usd_cost": mcu_health["used_usd"],
            "model": inference_result.get("model", ""),
            "latency_ms": inference_result.get("latency_ms", 0),
            "round": self.turn_manager.state.round_number if self.turn_manager else 0,
        }
        bus.publish("AGENT_REPORT", payload, sender=self.agent_name)

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

            # 2d. Verificar metabolismo (Token Tracking + Budget Checking)
            if self.token_tracker.needs_shredding():
                telemetry.info(f"🧹 [{self.agent_name}] Contexto saturado. Solicitando shredding...")
                # Destilar el system prompt si es necesario
                raw = [{"proponent": self.system_prompt}]
                self.system_prompt = self.shredder.distill(raw)
                self.token_tracker.reset()
                self.token_tracker.track_context(self.system_prompt)

            # --- NUEVO: Control Presupuestario (OSAA v6.0) ---
            mcu_health = self.mcu.check_health(self.mission_id)
            if mcu_health["status"] == "STARVING":
                telemetry.error(f"💸 [{self.agent_name}] ASFIXIA FINANCIERA: Presupuesto agotado (${mcu_health['used_usd']:.4f}).")
                result["status"] = "METABOLIC_EXHAUSTION"
                break
            elif mcu_health["status"] == "CONGESTED":
                telemetry.warning(f"⚠️ [{self.agent_name}] Alerta Metabólica: Presupuesto al {mcu_health['percent']:.1f}%.")

            # --- NUEVO: Neural Trace (OSAA v6.0) ---
            from opentelemetry import propagate
            from opentelemetry import trace as trace_api
            
            ctx = self.turn_manager.state.trace_context
            token = None
            if ctx:
                token = propagate.attach(ctx)
            
            tracer = get_tracer("agent_runner")
            with NeuralSpan.agent_span(tracer, f"Round {round_num + 1} - {self.agent_name}", current_task):
                # 2e. Inferencia
                telemetry.info(f"🤖 [{self.agent_name}] Invocando inferencia ({self.provider}/{self.model})...")
                inference_result = await self.llm.infer(
                    system_prompt=self.system_prompt,
                    debate_history=debate_history,
                    current_task=current_task,
                    allowed_tools=self.allowed_tools,
                )
                
                report = inference_result.get("content", "")
                tokens_in = self.token_tracker.estimate_tokens(self.system_prompt + current_task)
                tokens_out = inference_result.get("tokens_used", 0) - tokens_in # Aproximación
                if tokens_out < 0: tokens_out = inference_result.get("tokens_used", 0) # Fallback
                
                # Registrar consumo financiero
                self.mcu.record_consumption(
                    mission_id=self.mission_id,
                    agent=self.agent_name,
                    model=self.model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out
                )
                
                result["total_tokens"] += (tokens_in + tokens_out)

                if not report:
                    telemetry.error(f"❌ [{self.agent_name}] Inferencia retornó vacío.")
                    if token: propagate.detach(token)
                    continue

                # 2f. Emitir reporte
                self._emit_report(report, inference_result)
                result["rounds_completed"] = round_num + 1
                
                if token:
                    propagate.detach(token)

            report = inference_result.get("content", "")
            tokens_in = self.token_tracker.estimate_tokens(self.system_prompt + current_task)
            tokens_out = inference_result.get("tokens_used", 0) - tokens_in # Aproximación
            if tokens_out < 0: tokens_out = inference_result.get("tokens_used", 0) # Fallback
            
            # Registrar consumo financiero
            self.mcu.record_consumption(
                mission_id=self.mission_id,
                agent=self.agent_name,
                model=self.model,
                tokens_in=tokens_in,
                tokens_out=tokens_out
            )
            
            result["total_tokens"] += (tokens_in + tokens_out)

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

    # Inicializar Neural Trace
    initialize_tracer(f"agent-{args.agent_name}")

    # DEBUG: Verificar fcntl
    try:
        import fcntl
        telemetry.info(f"🧪 [DEBUG] fcntl verificado en {args.agent_name}")
    except Exception as e:
        telemetry.error(f"❌ [DEBUG] fcntl FALLÓ en {args.agent_name}: {e}")

    runner = AgentRunner(
        brain_path=args.brain,
        mission_id=args.mission_id,
        agent_name=args.agent_name,
    )

    try:
        result = await runner.run()
    except Exception as e:
        # --- EL GRITO DE MUERTE (Death Rattle) ---
        from core.event_bus import bus
        telemetry.error(f"💥 [FATAL] {args.agent_name} colapsó: {e}")
        
        payload = {
            "mission_id": args.mission_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        try:
            bus.publish("AGENT_FATAL_ERROR", payload, sender=args.agent_name)
        except:
            pass # No podemos hacer mucho más si el bus también falla
            
        sys.exit(1)

    # Exit code: 0 = OK, 1 = error, 2 = shutdown
    if result["status"] == "ERROR":
        sys.exit(1)
    elif result["status"] == "SHUTDOWN":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
