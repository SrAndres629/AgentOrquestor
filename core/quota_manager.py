import sys
import asyncio
import yaml
import os
import hashlib
from core.event_bus import bus
from core.memory_manager import vault

class QuotaManager:
    """Gestiona la rotación de modelos con Brain Handover."""
    def __init__(self, registry_path="agents/registry.yaml"):
        self.registry_path = registry_path
        self.current_tier = "tier_1_premium"

    def _log(self, msg: str):
        sys.stderr.write(msg + "\n")

    async def handle_api_error(self, data: dict, current_state_data: dict = None):
        error_msg = data.get("error", "")
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            self._log(f"⚠️ [QUOTA] Límite alcanzado en {self.current_tier}. Iniciando Brain Handover...")

            task_id = None
            if current_state_data:
                objective = str(current_state_data.get("task_manifest", {}).get("objective", "") or "")
                if objective:
                    task_id = hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12]
            
            # 1. Destilación Semántica antes de morir (Vanguardia)
            if current_state_data:
                await vault.save_consciousness_manifesto(current_state_data)
            
            await self.rotate_tier(reason="rate_limit", task_id=task_id)

    async def handle_vram_pressure(self, state_data: dict | None, used_mb: float | None = None, threshold_mb: float | None = None):
        used_txt = f"{used_mb:.0f}MB" if isinstance(used_mb, (int, float)) else "unknown"
        thr_txt = f"{threshold_mb:.0f}MB" if isinstance(threshold_mb, (int, float)) else "unknown"
        self._log(f"🔥 [QUOTA] Presión de VRAM detectada (used={used_txt}, threshold={thr_txt}). Brain Handover preventivo.")

        task_id = None
        if state_data:
            objective = str(state_data.get("task_manifest", {}).get("objective", "") or "")
            if objective:
                task_id = hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12]

        if state_data:
            await vault.save_consciousness_manifesto(state_data)

        await self.rotate_tier(reason="vram_pressure", task_id=task_id)

    async def rotate_tier(self, reason: str = "manual", task_id: str | None = None):
        try:
            with open(self.registry_path, "r") as f:
                registry = yaml.safe_load(f)
            
            tiers = registry.get("model_tiers", {})
            next_tier = tiers.get(self.current_tier, {}).get("fallback")

            if next_tier and next_tier != "hibernate":
                self._log(f"🔄 [QUOTA] Traspasando conciencia a: {next_tier} (reason={reason})")
                self.current_tier = next_tier
                await bus.publish("MODEL_ROTATED", data={
                    "new_tier": next_tier,
                    "config": tiers.get(next_tier)
                }, task_id=task_id)
            elif next_tier == "hibernate":
                self._log("💤 [QUOTA] No hay más cuota. Hibernación profunda.")
                await bus.publish("SYSTEM_HIBERNATE", task_id=task_id)
        except Exception as e:
            self._log(f"❌ [QUOTA] Error en rotación: {e}")

quota_manager = QuotaManager()
