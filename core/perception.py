"""
AgentOrquestor - Perception Engine (Tree-sitter & DTG)
=====================================================
Analizador estructural de código. Convierte archivos físicos en un 
Data Transformation Graph (DTG) matemático mediante tree-sitter.
Permite al agente "ver" dependencias y flujos sin leer texto plano.
"""

import os
from typing import Dict, Any, List
from tree_sitter import Language, Parser

# Asumimos gramáticas pre-compiladas para Python en Q1-2026
PY_LANGUAGE = Language('core/grammars/python.so', 'python')

class PerceptionEngine:
    """
    Motor de análisis profundo de código (AST -> DTG).
    """
    def __init__(self):
        self.parser = Parser()
        self.parser.set_language(PY_LANGUAGE)

    def generate_dtg(self, file_path: str) -> Dict[str, Any]:
        """
        Lee un archivo y genera un Grafo de Transformación de Datos.
        """
        if not os.path.exists(file_path):
            return {}

        with open(file_path, "rb") as f:
            tree = self.parser.parse(f.read())
            
        root_node = tree.root_node
        
        # Extracción de Nodos (Funciones, Clases, Asignaciones)
        dtg = {
            "nodes": [],
            "edges": [], # Dependencias y flujo de datos
            "complexity_score": 0
        }
        
        # Recorrido del AST para mapear el DTG
        cursor = tree.walk()
        reached_root = False
        while not reached_root:
            node_type = cursor.node.type
            if node_type in ["function_definition", "class_definition"]:
                dtg["nodes"].append({
                    "id": cursor.node.id,
                    "type": node_type,
                    "name": self._get_node_name(cursor.node),
                    "range": [cursor.node.start_byte, cursor.node.end_byte]
                })
            
            # Navegación del árbol (DFS)
            if cursor.goto_first_child():
                continue
            if cursor.goto_next_sibling():
                continue
            
            retracing = True
            while retracing:
                if not cursor.goto_parent():
                    retracing = False
                    reached_root = True
                if cursor.goto_next_sibling():
                    retracing = False

        dtg["complexity_score"] = len(dtg["nodes"])
        return dtg

    def _get_node_name(self, node) -> str:
        """Extrae el identificador del nodo (ej: nombre de la función)."""
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return "anonymous"

perception = PerceptionEngine()
