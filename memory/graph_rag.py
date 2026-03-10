"""
AgentOrquestor - Knowledge Graph (GraphRAG)
===========================================
Implementa el mapeo lógico de relaciones del código. 
Utiliza el DTG Context para responder consultas estructurales como 
"¿Qué funciones dependen de X?" o "¿Cuál es el impacto de cambiar Y?".
"""

import networkx as nx
from typing import Dict, Any, List, Set
from .vector_store import vector_store
from .crypto_manager import crypto

class GraphRAGManager:
    """
    Gestor del Grafo de Conocimiento Estructural.
    """
    def __init__(self):
        # Grafo en memoria para navegación rápida de dependencias
        self.graph = nx.DiGraph()

    def update_graph_from_dtg(self, dtg_context: Dict[str, Any]):
        """Mapea los nodos y aristas del DTG al Grafo de Conocimiento."""
        nodes = dtg_context.get("nodes", [])
        edges = dtg_context.get("edges", [])
        
        for node in nodes:
            self.graph.add_node(
                node["name"], 
                type=node["type"], 
                range=node["range"]
            )
            
        for edge in edges:
            # Relaciones del tipo: source -> calls -> target
            self.graph.add_edge(edge["source"], edge["target"], relationship="calls")

    def retrieve_context(self, query: str, target_file: str) -> Dict[str, Any]:
        """
        Devuelve el contexto semántico (ChromaDB) y el estructural (GraphRAG).
        """
        # 1. Recuperación Semántica (Cifrada)
        semantic_results = vector_store.search_vault(query, n_results=2)
        decrypted_heuristics = []
        for doc in semantic_results.get("documents", [[]])[0]:
            try:
                decrypted_heuristics.append(crypto.decrypt_payload(doc))
            except Exception:
                pass

        # 2. Recuperación Estructural (GraphRAG)
        # Buscamos dependencias directas e indirectas (Impact Analysis)
        dependencies = {}
        if self.graph.has_node(target_file):
            # Obtener predecesores (quién llama a este archivo/función)
            callers = list(self.graph.predecessors(target_file))
            # Obtener sucesores (a quién llama este archivo/función)
            callees = list(self.graph.successors(target_file))
            
            dependencies = {
                "impacted_by": callers,
                "calls_to": callees
            }

        return {
            "heuristics": decrypted_heuristics,
            "logical_dependencies": dependencies,
            "query_intent": query
        }

# Singleton de GraphRAG
graph_rag = GraphRAGManager()
