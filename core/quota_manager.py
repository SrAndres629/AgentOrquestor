import asyncio
import yaml
import os
from core.event_bus import bus

class QuotaManager:
    """Gestiona la rotación de modelos para maximizar el tiempo de vida autónomo."""
    def __init__(self, registry_path="agents/registry.yaml"):
        self.registry_path = registry_path
        self.current_tier = "tier_1_premium"
        self.history = []

    async def handle_api_error(self, data: dict):
        """Escucha errores de Rate Limit (429) o Quota (403)."""
        error_msg = data.get("error", "")
        # Detectar patrones de cuota agotada
        if "429" in error_msg or "rate_limit" in error_msg.lower() or "quota" in error_msg.lower():
            print(f"⚠️ [QUOTA] Límite alcanzado en {self.current_tier}. Iniciando Cascada de Fallback...")
            await self.rotate_tier()

    async def rotate_tier(self):
        """Mueve el sistema al siguiente nivel de inteligencia disponible."""
        try:
            with open(self.registry_path, "r") as f:
                registry = yaml.safe_load(f)
            
            tiers = registry.get("model_tiers", {})
            current_cfg = tiers.get(self.current_tier, {})
            next_tier = current_cfg.get("fallback")

            if next_tier and next_tier != "hibernate":
                print(f"🔄 [QUOTA] Rotando de {self.current_tier} -> {next_tier}")
                self.current_tier = next_tier
                await bus.publish("MODEL_ROTATED", data={
                    "new_tier": next_tier,
                    "config": tiers.get(next_tier)
                })
            elif next_tier == "hibernate":
                print("💤 [QUOTA] Todos los recursos agotados. Hibernando estado...")
                await bus.publish("SYSTEM_HIBERNATE", data={"reason": "NO_QUOTA_REMAINING"})
        except Exception as e:
            print(f"❌ [QUOTA] Error crítico en rotación: {e}")

quota_manager = QuotaManager()