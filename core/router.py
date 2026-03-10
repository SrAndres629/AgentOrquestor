"""
AgentOrquestor - Capa 0: Enrutador Semántico (Semantic Router)
==============================================================
Intercepta tareas repetitivas antes de activar la etapa costosa de LangGraph
(que despertaría el modelo de validación y draft model en el Swarm).

Opera estrictamente sobre CPU para dejar libre la VRAM (6GB) usando el modelo
minimizado all-MiniLM-L6-v2, logrando un vector de embedding ligero.
Si una tarea reciente supera el umbral de similitud semántica, extraemos el 
parche diff de la DB local (SQLite / GraphRAG) para retorno determinista Inmediato.
"""

import os
import sqlite3
from typing import Optional, Dict, Any

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None

# Caché Singleton del modelo de CPU
_cpu_encoder = None

def get_encoder() -> 'SentenceTransformer':
    """Inicializa under-demand el modelo de embedding para uso de RAM, no VRAM."""
    global _cpu_encoder
    if _cpu_encoder is None:
        if SentenceTransformer is None:
            raise RuntimeError("La librería 'sentence-transformers' no está instalada.")
        
        # Modelo estricto a CPU: 384 dim, ~80MB en RAM.
        _cpu_encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    return _cpu_encoder


def _secure_db_path() -> str:
    """Respeta el confinamiento estricto a la carpeta del proyecto para SQLite."""
    project_root = os.path.abspath(os.getcwd())
    db_file = os.path.join(project_root, 'memory', 'graph', 'semantic_cache.db')
    
    # Path Traversal Guard de seguridad (Inyección base de manifiesto)
    if not os.path.abspath(db_file).startswith(project_root):
        raise SecurityError("Ruta de grafo fuera del límite de confinamiento permitido.")
    return db_file


def get_semantic_match(query: str, threshold: float = 0.95) -> Optional[Dict[str, Any]]:
    """
    Busca heurísticamente tareas resueltas en el Data Transformation Graph / GraphRAG.
    
    Args:
        query: Tarea entrante interceptada del MCP
        threshold: 0.95 estricto para considerarlo re-utilizable (Zero-Shot Match)
        
    Returns:
        Si match > umbral, un diccionario con el 'diff_patch' o 'cached_action'.
        Ninguno (None) si debe arrancar LangGraph el Swarm AI completo.
    """
    encoder = get_encoder()
    query_emb = encoder.encode(query, convert_to_tensor=True)
    
    # Aquí simulamos la capa GraphRAG SQLite por propósitos de scaffolding de la caché.
    # En Q1-2026 esto apuntará al almacén DTG WAL.
    db_path = _secure_db_path()
    
    if not os.path.exists(db_path):
        return None
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Búsqueda escalar predeterminada (Asumir tabla pre-existente con embs precomputados)
        # Nota: En prod, esto se reemplazará con libSQL o faiss sqlite VSS.
        cursor.execute("SELECT id, intent_query, diff_patch FROM intent_cache")
        cached_intents = cursor.fetchall()
        
        best_score = 0.0
        best_match = None
        
        for cid, intent_query, diff_patch in cached_intents:
            cached_emb = encoder.encode(intent_query, convert_to_tensor=True)
            score = util.cos_sim(query_emb, cached_emb).item()
            
            if score > best_score:
                best_score = score
                best_match = {"id": cid, "score": score, "diff_patch": diff_patch}
                
        if best_match and best_match["score"] >= threshold:
            return best_match
            
    except sqlite3.OperationalError:
        # En caso de que el almacén SQLite RAG no esté inicializado
        pass
    finally:
        if 'conn' in locals():
            conn.close()
            
    return None
