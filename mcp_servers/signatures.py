"""
AgentOrquestor - Unified Tool Reasoning
=======================================
Firma de razonamiento avanzada para MCPs de herramienta única.
Utiliza modelos mentales para descomponer objetivos complejos en 
acciones atómicas internas.
"""

import dspy

class UnifiedMissionSignature(dspy.Signature):
    """
    Actúa como un Orquestador Autónomo. 
    Analiza la misión, aplica Pensamiento Sistémico para identificar dependencias 
    y ejecuta la secuencia óptima de acciones internas para resolver el problema.
    """
    
    mission_objective = dspy.InputField(desc="Objetivo final y restricciones de la misión.")
    context_environment = dspy.InputField(desc="Estado actual del sistema, variables y hardware.")
    
    mental_model_analysis = dspy.OutputField(
        desc="Análisis detallado usando Primeros Principios y Pensamiento Inverso."
    )
    execution_plan = dspy.OutputField(
        desc="Secuencia lógica de pasos internos para completar la misión."
    )
    final_output = dspy.OutputField(
        desc="Resultado final consolidado de la operación."
    )
    verification_report = dspy.OutputField(
        desc="Validación de que el resultado cumple con el objetivo inicial."
    )
