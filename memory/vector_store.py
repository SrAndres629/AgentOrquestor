"""
AgentOrquestor - Physical Vector Store (ChromaDB)
=================================================
Almacén vectorial basado en disco. 
Utiliza PersistentClient para evitar el uso de RAM y embeddings ligeros (CPU-only) 
para la búsqueda semántica de heurísticas y código cifrado.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

class VectorStoreManager:
    """
    Gestor de ChromaDB persistente en disco.
    """
    def __init__(self, db_path: str = "memory/graph/chroma_db"):
        # Asegurar ruta absoluta para persistencia en disco
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.db_path = os.path.join(project_root, db_path)
        os.makedirs(self.db_path, exist_ok=True)
        
        # 1. Cliente persistente (Backend SQLite)
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # 2. Embedding Function Ligera (CPU Only)
        # 384 dimensiones, modelo all-MiniLM-L6-v2 (~80MB RAM)
        self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cpu"
        )
        
        # 3. Colección Principal de Heurísticas
        self.vault = self.client.get_or_create_collection(
            name="heuristics_vault",
            embedding_function=self.embedder
        )

    def add_to_vault(self, content: str, metadata: Dict[str, Any], id: str):
        """Añade una entrada a la base vectorial."""
        self.vault.add(
            documents=[content],
            metadatas=[metadata],
            ids=[id]
        )

    def search_vault(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """Busca coincidencias semánticas en el almacén vectorial."""
        return self.vault.query(
            query_texts=[query],
            n_results=n_results
        )

# Singleton del Almacén Vectorial
vector_store = VectorStoreManager()
