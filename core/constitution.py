"""
OSAA v6.0 — Global Constitution (Directivas del Sistema)
========================================================
Este módulo centraliza las leyes que rigen a todos los agentes.
Ahora utiliza el PerceptionEngine para leer las guías dinámicamente.
"""

from core.perception import engine as perception_engine

def get_global_directives(agent_name: str = "Generic") -> str:
    """
    Retorna el bloque de directivas según el rol del agente.
    Utiliza el PerceptionEngine para ensamblar la mente desde las guías OSAA v6.0.
    """
    return perception_engine.assemble_mind(agent_name)
