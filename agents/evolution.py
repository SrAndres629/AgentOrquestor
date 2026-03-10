"""
AgentOrquestor - DPO Evolution Engine
=====================================
Implementa el bucle de Direct Preference Optimization (DPO). 
Captura pares de (Elegido/Rechazado) tras la revisión humana para 
el reentrenamiento asíncrono del enjambre.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class EvolutionEngine:
    """
    Motor de aprendizaje por refuerzo basado en feedback humano.
    """
    def __init__(self, dataset_path: str = "memory/graph/dpo_pairs.jsonl"):
        self.dataset_path = dataset_path
        os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)

    def record_preference(self, prompt: str, rejected_response: str, chosen_response: str):
        """
        Registra un par DPO (Chosen vs Rejected) para el entrenamiento de adaptadores LoRA.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "chosen": chosen_response,
            "rejected": rejected_response,
            "metadata": {
                "system": "AgentOrquestor-v1",
                "hardware_context": "RTX3060-6GB-VRAM"
            }
        }
        
        # Escritura atómica en el dataset (JSONL para streaming de entrenamiento)
        with open(self.dataset_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def analyze_stagnation(self) -> bool:
        """
        Analiza si el modelo está cometiendo errores repetitivos para 
        disparar una alerta de 'Fine-Tuning Requerido'.
        """
        if not os.path.exists(self.dataset_path):
            return False
            
        with open(self.dataset_path, "r") as f:
            lines = f.readlines()
            # Si hay más de 10 rechazos en la última sesión, sugerimos evolución
            return len(lines) > 10

# Singleton de Evolución
evolution_engine = EvolutionEngine()
