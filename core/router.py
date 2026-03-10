"""
AgentOrquestor - Capa 0: Enrutador Semántico (Cloud API Edition)
==============================================================
Utiliza OpenRouter/Voyage para embeddings de alta precisión.
Elimina la carga de CPU/GPU local para optimizar el i9/RTX3060.
"""

import os
import sqlite3
import httpx
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env local
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

def get_voyage_embedding(text: str) -> List[float]:
    """
    Llama a Voyage AI o OpenRouter para obtener el vector semántico.
    Nota: voyage-code-2 es el estándar de oro para embeddings de código.
    """
    # Si no hay API Key, devolvemos un vector nulo para evitar crasheos (Fallback)
    if "REPLACE_WITH_YOUR_KEY" in OPENROUTER_API_KEY or not OPENROUTER_API_KEY:
        return [0.0] * 384 # Dimensión del anterior local

    try:
        # Llamada a OpenRouter (O Voyage AI directo)
        with httpx.Client() as client:
            response = client.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                json={
                    "model": "voyageai/voyage-code-2",
                    "input": text
                },
                timeout=10.0
            )
            return response.json()["data"][0]["embedding"]
    except Exception:
        return [0.0] * 384

def get_semantic_match(query: str, threshold: float = 0.95) -> Optional[Dict[str, Any]]:
    """
    Busca heurísticamente tareas resueltas en el Data Transformation Graph (Capa 0).
    Utiliza el motor de embeddings de la nube para precisión quirúrgica.
    """
    query_emb = get_voyage_embedding(query)
    
    # Simulación de búsqueda en base de datos local (SQLite)
    # Aquí es donde el GraphRAG de AgentOrquestor recupera las soluciones pasadas.
    db_path = os.path.join(os.path.dirname(__file__), "../memory/graph/semantic_cache.db")
    
    if not os.path.exists(db_path):
        return None
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, intent_query, diff_patch FROM intent_cache")
        cached_intents = cursor.fetchall()
        
        best_score = 0.0
        best_match = None
        
        # En una implementación real 2026, esto usaría pgvector o faiss-sqlite
        for cid, intent_query, diff_patch in cached_intents:
            # Nota: Esto es ineficiente (re-embed de caché). En prod se guarda el vector.
            cached_emb = get_voyage_embedding(intent_query)
            
            # Cálculo de similitud coseno (Simulado)
            import numpy as np
            def cos_sim(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
            score = cos_sim(query_emb, cached_emb)
            if score > best_score:
                best_score = score
                best_match = {"id": cid, "score": score, "diff_patch": diff_patch}
                
        if best_match and best_match["score"] >= threshold:
            return best_match
            
    except Exception:
        pass
    finally:
        if "conn" in locals(): conn.close()
            
    return None
