"""
Test Riguroso de Aislamiento para cognitive_cortex (Sequential Thinking Nativo)
"""

import sys
import unittest
from core.cognitive_cortex import cognitive_cortex, ThoughtData

class TestSequentialThinkingCore(unittest.TestCase):
    def test_schema_rejection_on_invalid_input(self):
        """Verificar resiliencia contra alucinaciones del LLM."""
        # Payload sin required keys
        payload = {"thought": "This is a thought"}
        result = cognitive_cortex.process_thought(payload)
        self.assertEqual(result.get("status"), "ERROR")
        self.assertIn("Falló validación", result.get("message", ""))

    def test_valid_thought_chain_and_branching(self):
        """Verificar memoria de cadena de pensamiento y heurística de recursividad."""
        payload_1 = {
            "thought": "Hypothesis 1",
            "thoughtNumber": 1,
            "totalThoughts": 3,
            "nextThoughtNeeded": True
        }
        res1 = cognitive_cortex.process_thought(payload_1)
        self.assertEqual(res1.get("status"), "SUCCESS")
        self.assertEqual(res1.get("thoughtHistoryLength"), 1)
        
        # Test ramificación
        payload_2 = {
            "thought": "Wait, let's explore an alternative.",
            "thoughtNumber": 2,
            "totalThoughts": 4, # El agente ajusta dinámicamente
            "nextThoughtNeeded": True,
            "branchId": "branch_alpha",
            "branchFromThought": 1
        }
        res2 = cognitive_cortex.process_thought(payload_2)
        self.assertEqual(res2.get("status"), "SUCCESS")
        self.assertIn("branch_alpha", res2.get("branches", []))

if __name__ == "__main__":
    unittest.main()
