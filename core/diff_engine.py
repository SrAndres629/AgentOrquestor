"""
AgentOrquestor - Perception & Diff Engine
=========================================
Implementa AST-Aware Chunking (Tree-sitter) y generación de parches Unified Diffs.
Permite al agente entender el código por bloques lógicos y proponer cambios mínimos.
"""

import difflib
from typing import List, Dict, Any
from core.perception import perception # Importamos el motor base

class CodeSpecialist:
    """
    Especialista en fragmentación y reconstrucción de código.
    """
    
    def get_ast_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Fragmenta el código en bloques lógicos (clases/funciones) 
        respetando las fronteras del AST.
        """
        dtg = perception.generate_dtg(file_path)
        chunks = []
        
        with open(file_path, "r") as f:
            content = f.read()
            
        for node in dtg.get("nodes", []):
            start, end = node["range"]
            chunks.append({
                "name": node["name"],
                "type": node["type"],
                "content": content[start:end]
            })
        return chunks

    def generate_unified_diff(self, original_code: str, modified_code: str, file_name: str) -> str:
        """
        Genera un parche estándar (Unified Diff) eficiente con difflib.
        """
        original_lines = original_code.splitlines(keepends=True)
        modified_lines = modified_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines, 
            modified_lines, 
            fromfile=f"a/{file_name}", 
            tofile=f"b/{file_name}"
        )
        return "".join(diff)

diff_engine = CodeSpecialist()
