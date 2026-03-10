"""
AgentOrquestor - Persistence Layer (SQLite WAL)
==============================================
Gestiona la persistencia del estado del grafo en disco.
Utiliza SqliteSaver para permitir el "Wake-on-Call" y liberar la RAM 
cuando el enjambre está en reposo.
"""

import sqlite3
import os
from langgraph.checkpoint.sqlite import SqliteSaver

def get_checkpointer() -> SqliteSaver:
    """
    Inicializa y retorna el checkpointer de SQLite con modo WAL activo.
    """
    db_path = "core/database.db"
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Conexión persistente con optimizaciones para concurrencia (IDE Antigravity)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") # Write-Ahead Logging
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    return SqliteSaver(conn)

# Singleton para el orquestador
memory = get_checkpointer()
