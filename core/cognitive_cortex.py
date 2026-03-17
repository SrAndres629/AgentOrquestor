"""
Cognitive Cortex (Sequential Thinking Native Implementation)
Provee la capacidad de ramificación lógica y pensamiento estructurado al enjambre.
Maximiza la soberanía al no requerir un servidor Node.js/Stdio externo.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ThoughtData(BaseModel):
    thought: str
    thoughtNumber: int
    totalThoughts: int
    isRevision: bool = False
    revisesThought: Optional[int] = None
    branchFromThought: Optional[int] = None
    branchId: Optional[str] = None
    needsMoreThoughts: bool = False
    nextThoughtNeeded: bool

class SequentialThinkingCore:
    def __init__(self):
        self.thought_history: List[ThoughtData] = []
        self.branches: Dict[str, List[ThoughtData]] = {}
        # Pre-instancia de LLMBridge para razonamiento puro sin herramientas
        from core.llm_bridge import LLMBridge
        import os
        provider = os.getenv("PLANNER_PROVIDER", "groq")
        model = os.getenv("PLANNER_MODEL", "llama-3.3-70b-versatile")
        api_key = LLMBridge.PROVIDER_KEYS.get(provider, lambda: os.getenv("GROQ_API_KEY", ""))()
        
        self.llm = LLMBridge(
            provider=provider,
            model=model,
            api_key=api_key,
            mcp_proxy=None, # Razonamiento aislado
            agent_name="CognitiveCortex"
        )

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "sequentialthinking",
                "description": (
                    "Herramienta de razonamiento reflexivo. "
                    "Úsala para desglosar problemas complejos, planificar con revisión, analizar errores "
                    "o generar hipótesis antes de tomar una decisión final (ej. antes de modificar archivos)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "thought": {"type": "string", "description": "El pensamiento analítico actual."},
                        "nextThoughtNeeded": {"type": "boolean", "description": "¿Iteramos de nuevo?"},
                        "thoughtNumber": {"type": "integer", "description": "Índice actual del pensamiento."},
                        "totalThoughts": {"type": "integer", "description": "Total de pasos cognitivos estimados."},
                        "isRevision": {"type": "boolean"},
                        "revisesThought": {"type": "integer"},
                        "branchFromThought": {"type": "integer"},
                        "branchId": {"type": "string"},
                        "needsMoreThoughts": {"type": "boolean"}
                    },
                    "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
                }
            }
        }

    def process_thought(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Parse validation via Pydantic model (or just dict extraction)
            thought_data = ThoughtData(**args)
            
            # Formateamos el resultado de forma compatible
            self.thought_history.append(thought_data)
            
            if thought_data.branchId:
                if thought_data.branchId not in self.branches:
                    self.branches[thought_data.branchId] = []
                self.branches[thought_data.branchId].append(thought_data)

            return {
                "status": "SUCCESS",
                "thoughtNumber": thought_data.thoughtNumber,
                "totalThoughts": thought_data.totalThoughts,
                "nextThoughtNeeded": thought_data.nextThoughtNeeded,
                "branches": list(self.branches.keys()),
                "thoughtHistoryLength": len(self.thought_history)
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Falló validación de esquema cognitivo: {str(e)}"}

    async def generate_zero_shot_thought(self, agent_role: str, context: str, current_task: str) -> str:
        """
        Genera un árbol de pensamiento rápido sin invocación de herramientas.
        Este es el "Cognitive Pre-Flight" inyectado axiomáticamente.
        """
        from core.telemetry import telemetry
        import json
        
        telemetry.info(f"🧠 [COGNITIVE_CORTEX] Generando pensamiento zero-shot para {agent_role}...")
        
        system_prompt = (
            f"Eres el Córtex Prefrontal interno del agente con rol: {agent_role}.\n"
            "Tu único propósito es pensar paso a paso (Chain of Thought) antes de que el agente actúe.\n"
            "Dado el contexto y la tarea actual, desglosa el problema, evalúa riesgos y formula un plan de acción lógico.\n"
            "IMPORTANTE: NO ESTÁS EJECUTANDO LA TAREA. SOLO ESTÁS PENSANDO EN CÓMO DEBERÍA EJECUTARSE.\n"
            "Responde de manera concisa y altamente estructurada. Evita saludos."
        )
        
        user_message = (
            f"Contexto o Historial Reciente:\n{context}\n\n"
            f"Tarea actual propuesta:\n{current_task}\n\n"
            "Escribe tu razonamiento secuencial."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        res = await self.llm.infer(messages=messages, mission_id="cognitive_preflight")
        
        if res["status"] == "OK":
            telemetry.info(f"✅ [COGNITIVE_CORTEX] Razonamiento cristalizado.")
            return res["content"]
        else:
            telemetry.warning(f"⚠️ [COGNITIVE_CORTEX] Fallo en pre-flight: {res['content']}")
            return "El córtex no pudo formular un pensamiento estructurado previo. Actúa con precaución extrema."

# Singleton instance for the agent process
cognitive_cortex = SequentialThinkingCore()
