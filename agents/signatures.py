"""
AgentOrquestor - DSPy Signatures
================================
Definiciones de firmas de razonamiento (Reasoning Signatures) para el módulo DSPy.
Estas firmas estructuran la entrada/salida de los LLMs para tareas de refactorización
y auditoría de seguridad, permitiendo la optimización automática de prompts (Teleprompters).
"""

import dspy
from typing import List

class CodeRefactorSignature(dspy.Signature):
    """
    Genera código refactorizado y optimizado basado en un Grafo de Transformación de Datos (DTG).
    Debe priorizar la eficiencia, la legibilidad y el cumplimiento de los estándares del proyecto.
    """
    
    dtg_context = dspy.InputField(
        desc="Representación del Grafo de Transformación de Datos (contexto estructural)."
    )
    task_description = dspy.InputField(
        desc="Descripción detallada de la tarea de refactorización o implementación."
    )
    
    reasoning_chain = dspy.OutputField(
        desc="Cadena de pensamiento (CoT) paso a paso explicando las decisiones arquitectónicas."
    )
    refactored_code = dspy.OutputField(
        desc="Bloque de código final refactorizado (listo para producción)."
    )


class SecurityAuditSignature(dspy.Signature):
    """
    Audita fragmentos de código en busca de vulnerabilidades de seguridad, 
    fugas de memoria o violaciones de restricciones de hardware.
    """
    
    code_snippet = dspy.InputField(
        desc="El código fuente propuesto para auditoría."
    )
    context_constraints = dspy.InputField(
        desc="Restricciones de seguridad y hardware (e.g., uso de VRAM, aislamiento de directorios)."
    )
    
    is_approved = dspy.OutputField(
        desc="Booleano (True/False) indicando si el código pasa la auditoría."
    )
    risk_analysis = dspy.OutputField(
        desc="Lista de riesgos identificados o 'Ninguno' si es seguro."
    )
    mitigation_suggestions = dspy.OutputField(
        desc="Sugerencias concretas para mitigar los riesgos detectados, si los hay."
    )
