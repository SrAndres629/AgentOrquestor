"""
AgentOrquestor - DSPy Signatures (v2.3)
================================
Añadido: IntrospectionSignature para Autoconciencia y Curación.
"""

import dspy
from typing import List, Literal

class IntrospectionSignature(dspy.Signature):
    """Analiza un error propio y mapea la herramienta necesaria para repararlo."""
    error_log = dspy.InputField(desc="Fragmento del log de error detectado.")
    available_tools = dspy.InputField(desc="Lista de herramientas (Skills) cargadas en el sistema.")
    
    root_cause = dspy.OutputField(desc="Análisis técnico del origen del fallo.")
    healing_plan = dspy.OutputField(desc="Pasos exactos para la autoreparación.")
    selected_tool = dspy.OutputField(desc="La herramienta específica que se debe invocar.")


class MentalModelSignature(dspy.Signature):
    """
    Obliga al System_Architect a estructurar su salida aplicando modelos mentales.
    """
    context = dspy.InputField(desc="Contexto técnico del problema y arquitectura actual.")
    requirement = dspy.InputField(desc="Requerimiento funcional o técnico a implementar.")
    mental_model = dspy.InputField(desc="Modelo mental a aplicar.")

    structural_analysis = dspy.OutputField(desc="Análisis profundo basado en el modelo mental.")
    proposed_strategy = dspy.OutputField(desc="Estrategia técnica detallada.")
    affected_components = dspy.OutputField(desc="Lista de módulos y archivos impactados.")


class CodeRefactorSignature(dspy.Signature):
    """Genera código refactorizado basado en DTG."""
    dtg_context = dspy.InputField(desc="Grafo de Transformación de Datos.")
    task_description = dspy.InputField(desc="Descripción de la tarea.")
    reasoning_chain = dspy.OutputField(desc="CoT paso a paso.")
    refactored_code = dspy.OutputField(desc="Bloque de código final.")


class SecurityAuditSignature(dspy.Signature):
    """Audita código en busca de vulnerabilidades."""
    code_snippet = dspy.InputField(desc="Código fuente para auditoría.")
    context_constraints = dspy.InputField(desc="Restricciones de seguridad y hardware.")
    is_approved = dspy.OutputField(desc="Booleano indicando si pasa la auditoría.")
    risk_analysis = dspy.OutputField(desc="Análisis de riesgos.")
    mitigation_suggestions = dspy.OutputField(desc="Sugerencias de mitigación.")
