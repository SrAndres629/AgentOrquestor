"""
AgentOrquestor - Unified MCP Template (1-Tool Architecture)
===========================================================
Implementa el patrón de Herramienta Única Avanzada. 
Sustituye múltiples herramientas granulares por una sola interfaz de misión 
basada en modelos mentales de razonamiento sistémico.
"""

import asyncio
import json
import dspy
from mcp.server import Server
from .signatures import UnifiedMissionSignature

class UnifiedMCPServer:
    """
    Servidor MCP de Herramienta Única con Inteligencia de Misión.
    """
    def __init__(self, name: str):
        self.server = Server(f"{name}-unified-agent")
        self.setup_tools()

    def setup_tools(self):
        """Define la única herramienta que reemplaza a todas."""
        
        @self.server.list_tools()
        async def handle_list_tools():
            return [
                {
                    "name": "execute_mission",
                    "description": (
                        "Herramienta única para todas las operaciones en este servidor. "
                        "Acepta una misión semántica, aplica modelos mentales avanzados "
                        "y devuelve la resolución completa de la tarea."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "mission": {"type": "string", "description": "Objetivo detallado de la misión."},
                            "context": {"type": "object", "description": "Contexto técnico adicional del entorno."}
                        },
                        "required": ["mission"]
                    }
                }
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            if name != "execute_mission":
                raise ValueError(f"Herramienta desconocida: {name}. Usa 'execute_mission'.")

            # 1. Recuperamos la misión y el contexto
            mission = arguments.get("mission")
            context = arguments.get("context", {})

            # 2. Razonamiento Mental (Simulado con DSPy Predictor)
            # En producción esto conectaría con el motor DSPy optimizado.
            predictor = dspy.Predict(UnifiedMissionSignature)
            reasoning = predictor(mission_objective=mission, context_environment=json.dumps(context))

            # 3. Ejecución de Operaciones Internas (Abstracción)
            # Aquí es donde el servidor traduce el razonamiento en llamadas internas 
            # (Ej: git push, comfyui run, etc.) de forma invisible para el usuario.
            
            # Simulamos ejecución basada en el 'execution_plan' de DSPy
            print(f"[*] Analizando Misión con Primeros Principios: {reasoning.mental_model_analysis[:50]}...")
            print(f"[*] Ejecutando Plan de Misión: {reasoning.execution_plan[:50]}...")

            return [
                {
                    "type": "text",
                    "text": json.dumps({
                        "status": "MISSION_ACCOMPLISHED",
                        "reasoning": reasoning.mental_model_analysis,
                        "plan": reasoning.execution_plan,
                        "result": reasoning.final_output,
                        "verification": reasoning.verification_report
                    }, indent=2)
                }
            ]

# Singleton para pruebas o despliegue
# github_unified = UnifiedMCPServer("github")
