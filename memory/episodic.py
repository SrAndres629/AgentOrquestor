"""
AgentOrquestor - Episodic Memory & ADR Distillation
===================================================
Gestiona la memoria episódica mediante Mem0. 
Extrae Decisiones Arquitectónicas (ADR) del debate y las guarda 
encriptadas para el aprendizaje continuo del enjambre.
"""

import os
import json
import hashlib
from mem0 import Memory
from typing import List, Dict, Any
from .crypto_manager import crypto
from .vector_store import vector_store

class EpisodicMemory:
    """
    Motor de aprendizaje episódico y destilación de lecciones.
    """
    def __init__(self):
        # Mem0 para extracción de recuerdos
        self.mem0 = Memory()

    def distill_lesson(self, chat_history: List[Dict[str, Any]], success: bool, objective: str):
        """
        Extrae y guarda la lección aprendida de una sesión del enjambre.
        """
        if not success: return # Solo aprendemos de éxitos demostrados

        # 1. Extracción de la decisión (Simplificado: Últimos mensajes del LeadDeveloper)
        last_messages = [m["content"] for m in chat_history[-3:] if m.get("role") != "system"]
        raw_lesson = "\n".join(last_messages)
        
        # 2. Resumen Semántico con Mem0
        memories = self.mem0.add(raw_lesson, user_id="agent_orquestor", metadata={"objective": objective})
        
        # 3. Almacenamiento Cifrado en la Bóveda Vectorial
        for mem in memories:
            # Encriptamos el contenido de la lección (Propiedad Intelectual)
            encrypted_data = crypto.encrypt_payload(mem["content"])
            
            # El ID se genera basándose en el contenido para evitar duplicados
            mem_id = f"adr_{hashlib.sha256(mem['content'].encode()).hexdigest()[:12]}"
            
            vector_store.add_to_vault(
                content=encrypted_data.decode(), # Almacenamos el token base64 cifrado
                metadata={"objective": objective, "type": "ADR"},
                id=mem_id
            )

# Singleton de Memoria Episódica
episodic = EpisodicMemory()
