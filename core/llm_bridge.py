import os
import json
import time
import httpx
import random
import asyncio
from typing import Dict, Any, List, Optional
from core.telemetry import telemetry
from core.metabolic_governor import mcu
from core.neural_trace import get_tracer, NeuralSpan

INFERENCE_TIMEOUT = 60.0

class LLMBridge:
    """
    Puente Universal de Inferencia OSAA v6.0.
    Centraliza llamadas a LLMs con soporte para:
    - Resiliencia Metabólica (Exponential Backoff).
    - Seguimiento de Costos (MCU).
    - Trazabilidad Neural (OTel).
    - Function Calling vía MCPProxy.
    """
    
    PROVIDER_ENDPOINTS = {
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    }

    PROVIDER_KEYS = {
        "openrouter": lambda: os.getenv("OPENROUTER_API_KEY", ""),
        "groq": lambda: os.getenv("GROQ_API_KEY", ""),
        "google": lambda: os.getenv("GOOGLE_API_KEY", ""),
    }

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        mcp_proxy: Any = None,
        agent_name: str = "GenericAgent"
    ):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.mcp = mcp_proxy
        self.agent_name = agent_name
        self.endpoint = self.PROVIDER_ENDPOINTS.get(self.provider, "")
        self._tool_calls_executed: List[Dict[str, Any]] = []

    def _build_messages(
        self,
        system_prompt: str,
        debate_history: List[Dict[str, str]],
        current_task: str,
    ) -> List[Dict[str, str]]:
        """
        Construye el array de mensajes OpenAI-compatible.
        Inyecta la Constitución Global OSAA v6.0.
        """
        from core.constitution import get_global_directives
        
        # Evitar doble inyección si el prompt ya viene blindado por PerceptionEngine
        if "[OSAA v6.0 CONSTITUTIONAL CORE]" in system_prompt:
            full_system_prompt = system_prompt
        else:
            constitution = get_global_directives(self.agent_name)
            full_system_prompt = f"{constitution}\n\n{system_prompt}"
        
        messages = [{"role": "system", "content": full_system_prompt}]

        for entry in debate_history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": current_task})
        return messages

    def _build_tool_definitions(self, allowed_tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Convierte el catálogo de MCPProxy a formato OpenAI function-calling."""
        if not self.mcp:
            return []
            
        catalog = self.mcp.get_available_tools()
        definitions = []

        for tool in catalog:
            name = tool["name"]
            is_sovereign = name in ["register_new_tool", "sequentialthinking"]
            
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
                                "agent_name": {"type": "string", "description": "Nombre del agente"},
                                "tool_name": {"type": "string", "description": "Nombre de la herramienta"}
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
                            "action": {"type": "string"},
                            "target": {"type": "string"},
                            "params": {"type": "object"},
                        },
                        "required": ["action"],
                    },
                },
            })

        return definitions

    async def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        allowed_tools: Optional[List[Dict[str, Any]]] = None,
        mission_id: str = "orphan"
    ) -> Dict[str, Any]:
        """Ejecuta inferencia con soporte de Function Calling y Backoff."""
        
        if not self.api_key:
            return {"status": "ERROR", "content": "API Key no configurada."}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/AgentOrquestor"
            headers["X-Title"] = "AgentOrquestor-Swarm"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if allowed_tools:
            payload["tools"] = allowed_tools

        start_time = time.time()
        tool_rounds = 0
        max_tool_rounds = 3
        
        try:
            while tool_rounds < max_tool_rounds:
                response_data = await self._raw_api_call(headers, payload, mission_id)
                
                # Procesar respuesta
                choice = response_data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls")

                # Registrar consumo metabólico
                usage = response_data.get("usage", {})
                mcu.record_consumption(
                    mission_id=mission_id,
                    agent_name="LLMBridge",
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                    model=self.model
                )

                if not tool_calls:
                    latency = (time.time() - start_time) * 1000
                    return {
                        "content": content,
                        "tokens_used": usage.get("total_tokens", 0),
                        "latency_ms": latency,
                        "status": "OK"
                    }

                # Ejecutar herramientas si existen
                if self.mcp:
                    telemetry.info(f"🔧 Ejecutando {len(tool_calls)} tool_calls...")
                    tool_results = await self._execute_tool_calls(tool_calls)
                    
                    # Añadir respuesta del asistente y resultados de herramientas al historial
                    messages.append(message)
                    messages.extend(tool_results)
                    payload["messages"] = messages
                    tool_rounds += 1
                else:
                    telemetry.warning("⚠️ Tool calls recibidas pero MCPProxy no está configurado.")
                    break

            return {"status": "ERROR", "content": "Límite de rondas de herramientas alcanzado."}

        except Exception as e:
            telemetry.error(f"❌ Error en LLMBridge: {str(e)}")
            return {"status": "ERROR", "content": str(e)}

    async def _raw_api_call(self, headers: Dict[str, str], payload: Dict[str, Any], mission_id: str) -> Dict[str, Any]:
        max_retries = 5
        base_delay = 2.0
        
        tracer = get_tracer("llm_bridge")
        with NeuralSpan.llm_span(tracer, "LLM Inference", self.model, str(payload.get("messages", ""))[:1000]):
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=INFERENCE_TIMEOUT) as client:
                        response = await client.post(self.endpoint, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        return response.json()
                    
                    if response.status_code == 429:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        telemetry.warning(f"⏳ Rate Limit (429). Reintento {attempt+1}/{max_retries} en {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                    
                    response.raise_for_status()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(base_delay * (attempt + 1))
            
            raise Exception("Máximo de reintentos alcanzado.")

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name")
            args = json.loads(fn.get("arguments", "{}"))
            
            res = await self.mcp.call_tool(name, args)
            results.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "content": json.dumps(res, ensure_ascii=False)
            })
        return results
