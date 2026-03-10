import asyncio
import yaml
import os
from core.event_bus import bus
from core.memory_manager import vault

class QuotaManager:
    """Gestiona la rotación de modelos con Brain Handover."""
    def __init__(self, registry_path="agents/registry.yaml"):
        self.registry_path = registry_path
        self.current_tier = "tier_1_premium"

    async def handle_api_error(self, data: dict, current_state_data: dict = None):
        error_msg = data.get("error", "")
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            print(f"⚠️ [QUOTA] Límite alcanzado en {self.current_tier}. Iniciando Brain Handover...")
            
            # 1. Destilación Semántica antes de morir (Vanguardia)
            if current_state_data:
                await vault.save_consciousness_manifesto(current_state_data)
            
            await self.rotate_tier()

    async def rotate_tier(self):
        try:
            with open(self.registry_path, "r") as f:
                registry = yaml.safe_load(f)
            
            tiers = registry.get("model_tiers", {})
            next_tier = tiers.get(self.current_tier, {}).get("fallback")

            if next_tier and next_tier != "hibernate":
                print(f"🔄 [QUOTA] Traspasando conciencia a: {next_tier}")
                self.current_tier = next_tier
                await bus.publish("MODEL_ROTATED", data={
                    "new_tier": next_tier,
                    "config": tiers.get(next_tier)
                })
            elif next_tier == "hibernate":
                print("💤 [QUOTA] No hay más cuota. Hibernación profunda.")
                await bus.publish("SYSTEM_HIBERNATE")
        except Exception as e:
            print(f"❌ [QUOTA] Error en rotación: {e}")

quota_manager = QuotaManager()