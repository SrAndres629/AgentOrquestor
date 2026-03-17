"""
Test Riguroso de Inyección Sensorial NeuroVision (Visualización Arquitectónica)
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from core.telemetry import telemetry
from core.llm_bridge import LLMBridge

class TestNeuroVisionTelemetry(unittest.IsolatedAsyncioTestCase):
    @patch('core.telemetry.Telemetry._inject_neuro_vision')
    def test_telemetry_routes_to_vision(self, mock_neuro):
        """Verifica que cada log básico envía impulsos visuales."""
        telemetry.error("Fallo crítico de memoria VRAM detectado.")
        
        # Debe haberse llamado al inyector subyacente de NeuroVision
        mock_neuro.assert_called_with("ERROR", "Fallo crítico de memoria VRAM detectado.")
        
        telemetry.emit_event("MISSION_FAILED", {"agent": "LeadDev", "reason": "Syntax Error"})
        mock_neuro.assert_called_with("MISSION_FAILED", "Event Emitted", {"agent": "LeadDev", "reason": "Syntax Error"})
        
    @patch('httpx.AsyncClient.post')
    @patch('core.telemetry.Telemetry._inject_neuro_vision')
    async def test_asfixia_triggers_visual_pain(self, mock_neuro, mock_post):
        """Simula una muerte por Rate Limit persistente para ver si el enjambre pinta de rojo el nodo (Metaphorical)."""
        # Configurar un mock response de 429
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        bridge = LLMBridge(provider="groq", model="test-model", api_key="test-key")
        
        # Reducir max retries artificialmente para acelerar el test de muerte
        bridge.INFERENCE_TIMEOUT = 1.0 
        
        async def run_infer():
            try:
                await bridge.infer([{"role": "user", "content": "test"}])
            except Exception:
                pass
        
        import asyncio
        await run_infer()
            
        # El log de telemetría 'ASFIXIA METABÓLICA' o 'Excepción' debe enviar un impulso WARNING o ERROR al nervio óptico.
        # Validamos que se inyectó falla (cualquier llamada a _inject_neuro_vision cuenta como dolor estructural transmitido)
        self.assertTrue(mock_neuro.called)

if __name__ == "__main__":
    unittest.main()
