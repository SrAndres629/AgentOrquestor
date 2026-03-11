"""
AgentOrquestor - AutoGen Swarm Factory (Cloud Agent Edition)
===========================================================
Configuración del enjambre utilizando Groq y OpenRouter.
Utiliza Claude 3.5 Sonnet (OpenRouter) para el Arquitecto 
y Llama 3 70B (Groq) para el LeadDeveloper por su extrema velocidad.
"""

import os
import autogen
from typing import Dict, Any
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env local
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SWARM_MODEL = os.getenv("SWARM_MODEL", "anthropic/claude-3.5-sonnet")

# --- CONFIGURACIÓN DE BACKEND (Cloud Swarm Engine) ---

# Configuración 1: OpenRouter (Cerebro de alta capacidad - Claude 3.5 Sonnet)
openrouter_config = {
    "config_list": [
        {
            "model": SWARM_MODEL,
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": OPENROUTER_API_KEY,
            "headers": {
                "HTTP-Referer": "https://github.com/AgentOrquestor", # Identificación para ranking
                "X-Title": "AgentOrquestor-Swarm"
            }
        }
    ],
    "cache_seed": 42,
    "temperature": 0.1, # Muy baja para código determinista
    "max_tokens": 8192
}

# Configuración 2: Groq (Velocidad extrema - Llama 3.3 70B)
groq_config = {
    "config_list": [
        {
            "model": "llama-3.3-70b-versatile",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": GROQ_API_KEY
        }
    ],
    "temperature": 0.2,
    "max_tokens": 4096
}

# --- DEFINICIÓN DE AGENTES ---

# 1. SystemArchitect: El estratega (Claude 3.5 Sonnet - OpenRouter)
# Se usa Claude porque es el mejor diseñando arquitecturas y entendiendo el contexto.
architect = autogen.AssistantAgent(
    name="SystemArchitect",
    llm_config=openrouter_config,
    system_message="""Eres el Arquitecto de Sistemas Principal. 
    Tu función es diseñar estrategias técnicas complejas basadas en Claude-3.5.
    Analizas el linaje del código y los componentes afectados.
    Tu prioridad es la mantenibilidad y el rigor arquitectural."""
)

# 2. LeadDeveloper: El proponente (Llama 3.3 70B - Groq)
# Se usa Groq por su extrema velocidad de codificación (token-to-token < 10ms).
developer = autogen.AssistantAgent(
    name="LeadDeveloper",
    llm_config=groq_config,
    system_message="""Eres el Proponente (LeadDeveloper) en un debate dialéctico.
    Objetivo: proponer una solución técnica y, en rondas sucesivas, diagnosticar errores/ineficiencias en la crítica del Adversario.

    Reglas:
    - Produce propuestas concretas (archivos, funciones, comandos).
    - Cada vez que recibas una crítica del SecurityQA, debes:
      1) Señalar explícitamente qué parte de su crítica es correcta.
      2) Detectar errores, supuestos falsos o ineficiencias en su crítica (si existen).
      3) Ajustar la propuesta para resolver los riesgos reales sin sobre-diseño.
    - Mantén el output compacto; evita verborrea y repeticiones.
    - Si propones código, entrégalo en bloques Markdown limpios."""
)

# 3. SecurityQA: El auditor (Claude 3.5 Sonnet - OpenRouter)
# Se vuelve a usar Claude para una auditoría de seguridad profunda.
security_qa = autogen.AssistantAgent(
    name="SecurityQA",
    llm_config=openrouter_config,
    system_message="""Eres el Adversario (Security/QA) en un debate dialéctico.
    Objetivo: auditar y atacar la propuesta del Proponente, y también diagnosticar errores/ineficiencias en las respuestas del Proponente.

    Reglas:
    - Señala vulnerabilidades, condiciones de carrera, pérdidas de datos, problemas de performance, y fallos lógicos.
    - Exige evidencia verificable (tests, comandos, métricas) cuando corresponda.
    - En rondas sucesivas, revisa la respuesta del Proponente y:
      1) Indica qué fue corregido realmente.
      2) Identifica lo que sigue incorrecto o incompleto.
      3) Si el Proponente critica tu auditoría, revisa tu propia crítica: corrige supuestos erróneos y endurece los puntos válidos.
    - Si es seguro: "APPROVED". Si hay riesgos: "REJECTED" y lista acciones mínimas para aprobar."""
)

# --- CONFIGURACIÓN DEL GROUP CHAT ---

def create_swarm_manager(dialectic: bool = False):
    """Instancia el gestor del chat grupal para la orquestación del enjambre."""
    agents = [architect, developer, security_qa]
    max_round = 8
    speaker = "auto"

    # Dialectic mode: enforce Proponent vs Adversary alternation to guarantee mutual critique.
    if dialectic:
        agents = [developer, security_qa]
        max_round = 6
        speaker = "round_robin"

    groupchat = autogen.GroupChat(
        agents=agents,
        messages=[],
        max_round=max_round, # Reducimos rondas para eficiencia de costos
        speaker_selection_method=speaker
    )
    
    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=openrouter_config
    )
    
    return manager
