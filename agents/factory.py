"""
AgentOrquestor - AutoGen Swarm Factory
======================================
Configuración del enjambre de agentes utilizando AutoGen.
Implementa el patrón Blackboard para la comunicación entre especialistas y 
aplica optimizaciones de VRAM (PyramidKV).
"""

import autogen
from typing import Dict, Any
from .signatures import CodeRefactorSignature, SecurityAuditSignature

# --- CONFIGURACIÓN DE BACKEND (Local Swarm Engine) ---
# Esta configuración asume un servidor de inferencia local (vLLM, Ollama o vLLM-OpenAI-API)
# o una configuración de entorno local para evitar dependencias de terceros como OpenRouter.
llm_config = {
    "config_list": [
        {
            "model": "deepseek-r1", # O el modelo que sirvas localmente
            "base_url": "http://localhost:8000/v1", # Endpoint estándar local
            "api_key": "not-needed-locally",
        }
    ],
    "cache_seed": 42,
    "temperature": 0.2,
    "max_tokens": 4096,
    "extra_body": {
        "kv_cache_policy": "PyramidKV",
        "kv_cache_ratio": 0.12,
        "speculative_decoding": True
    }
}

# --- DEFINICIÓN DE AGENTES ---

# 1. SystemArchitect: El estratega
architect = autogen.AssistantAgent(
    name="SystemArchitect",
    llm_config=llm_config,
    system_message="""Eres el Arquitecto de Sistemas. 
    Tu función es analizar el DTG (Data Transformation Graph) y diseñar la estrategia técnica.
    No escribes código final, sino que dictas las pautas de diseño y los componentes afectados.
    Debes asegurar que la solución sea escalable y eficiente en términos de hardware."""
)

# 2. LeadDeveloper: El implementador (Powered by DSPy)
developer = autogen.AssistantAgent(
    name="LeadDeveloper",
    llm_config=llm_config,
    system_message=f"""Eres el Desarrollador Líder.
    Tu objetivo es implementar el código refactorizado.
    Utilizas la firma de razonamiento DSPy: {CodeRefactorSignature.__doc__}
    Debes seguir estrictamente las pautas del Arquitecto."""
)

# 3. SecurityQA: El auditor (Veto Power)
security_qa = autogen.AssistantAgent(
    name="SecurityQA",
    llm_config=llm_config,
    system_message=f"""Eres el Auditor de Seguridad (QA).
    Analizas el código del LeadDeveloper buscando vulnerabilidades.
    Utilizas la firma de razonamiento DSPy: {SecurityAuditSignature.__doc__}
    Si encuentras riesgos, debes vetar la solución con 'REJECTED' y explicar los motivos.
    Si es seguro, confirma con 'APPROVED'."""
)

# --- CONFIGURACIÓN DEL GROUP CHAT (Blackboard Pattern) ---

def create_swarm_manager():
    """Instancia el gestor del chat grupal para la orquestación del enjambre."""
    groupchat = autogen.GroupChat(
        agents=[architect, developer, security_qa],
        messages=[],
        max_round=10,
        speaker_selection_method="auto",
        allow_repeat_speaker=False
    )
    
    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config
    )
    
    return manager
