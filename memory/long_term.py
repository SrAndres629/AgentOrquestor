"""
AgentOrquestor - Long-Term Memory (Mem0 & ChromaDB)
==================================================
Memoria persistente y destilada. 
Utiliza Mem0 para extraer heurísticas de tareas anteriores y 
las almacena en ChromaDB encriptada (AES-256) con Fernet.
"""

import chromadb
from mem0 import Memory
from cryptography.fernet import Fernet
import os
import json

class LongTermMemory:
    """
    Gestor de memoria a largo plazo para aprendizaje persistente.
    """
    def __init__(self, db_path: str = "memory/graph/chroma"):
        # 1. Configuración de ChromaDB (Vector Store)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="swarm_heuristics")
        
        # 2. Configuración de Mem0 (Gestor de recuerdos)
        self.mem0 = Memory()
        
        # 3. Encriptación (Seguridad de Heurísticas)
        # En producción, la clave vendría de un Key Vault
        key = Fernet.generate_key() 
        self.cipher = Fernet(key)

    def distill_and_store(self, task_result: str, objective: str):
        """
        Extrae el aprendizaje de la tarea y lo guarda encriptado.
        """
        # Extraer recuerdos clave con Mem0
        memories = self.mem0.add(task_result, user_id="agent_orquestor", metadata={"objective": objective})
        
        # Serializar y encriptar para ChromaDB
        for mem in memories:
            raw_mem = json.dumps(mem)
            encrypted_mem = self.cipher.encrypt(raw_mem.encode()).decode()
            
            self.collection.add(
                documents=[encrypted_mem],
                ids=[f"mem_{os.urandom(4).hex()}"],
                metadatas=[{"objective": objective}]
            )

    def retrieve_heuristics(self, query: str) -> str:
        """Busca recuerdos relevantes para la tarea actual."""
        results = self.collection.query(query_texts=[query], n_results=3)
        
        decrypted_mems = []
        for doc_list in results['documents']:
            for doc in doc_list:
                try:
                    decrypted = self.cipher.decrypt(doc.encode()).decode()
                    decrypted_mems.append(decrypted)
                except Exception:
                    pass
        return "\n".join(decrypted_mems)

# Singleton de memoria
memory_bank = LongTermMemory()
