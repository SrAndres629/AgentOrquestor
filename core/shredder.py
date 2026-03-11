import sys
import asyncio
import re
import difflib
import os
from types import SimpleNamespace
from typing import List, Dict, Any
from core.event_bus import bus
from core.memory_manager import vault
from core.telemetry import telemetry

class AdvancedContextShredder:
    def __init__(self, token_threshold=3000):
        self.token_threshold = token_threshold

    def _normalize(self, s: str) -> str:
        s = s.lower()
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"[^a-z0-9áéíóúñü :;.,_\\-]", "", s)
        return s

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        return difflib.SequenceMatcher(a=a, b=b).ratio()

    def _extract_lesson(self, content: str) -> str:
        upper = content.upper()
        for key in ("LESSON:", "LECCION:", "LECCIÓN:", "LEARNED:", "LECCION APRENDIDA:"):
            i = upper.find(key)
            if i != -1:
                tail = content[i : i + 400].strip()
                return f"{tail}\n(Pruned: repeated circular reasoning)"
        # Fallback: keep first ~200 chars as “lesson anchor”
        short = content.strip().splitlines()[0][:200]
        return f"LESSON: {short}\n(Pruned: repeated circular reasoning)"

    async def shred(self, state: Any):
        messages = getattr(state, "messages", None)
        if messages is None and isinstance(state, dict):
            messages = state.get("messages", [])
        messages = messages or []

        # --- Drift detection & semantic pruning (first principles) ---
        try:
            dtg_context = getattr(state, "dtg_context", None)
            if dtg_context is None and isinstance(state, dict):
                dtg_context = state.setdefault("dtg_context", {})
            dtg_context = dtg_context or {}

            drift_store: Dict[str, int] = dict(dtg_context.get("_drift_fingerprints") or {})
            window_norms: List[str] = []
            new_messages = []
            tokens_saved_est = 0
            pruned_count = 0

            for m in messages:
                content = getattr(m, "content", None)
                content = str(content) if content is not None else ""
                if not content:
                    new_messages.append(m)
                    continue

                is_ai = getattr(m, "type", "") == "ai" or m.__class__.__name__ == "AIMessage"
                if not is_ai:
                    new_messages.append(m)
                    continue

                norm = self._normalize(content)
                best_sim = 0.0
                best_norm = None
                for prev in window_norms[-30:]:
                    sim = self._similarity(norm, prev)
                    if sim > best_sim:
                        best_sim = sim
                        best_norm = prev

                if best_sim >= 0.85 and best_norm:
                    drift_store[best_norm] = int(drift_store.get(best_norm, 1)) + 1
                    repeats = drift_store[best_norm]
                    if repeats >= 3:
                        lesson = self._extract_lesson(content)
                        new_messages.append(SimpleNamespace(type="ai", content=lesson))
                        pruned_count += 1
                        tokens_saved_est += max(int((len(content) - len(lesson)) / 4), 0)
                        telemetry.emit_event(
                            "PRUNED_CIRCULAR_REASONING",
                            {
                                "similarity": round(best_sim, 4),
                                "repeats": repeats,
                                "tokens_saved_est": max(int((len(content) - len(lesson)) / 4), 0),
                            },
                        )
                        continue

                window_norms.append(norm)
                new_messages.append(m)

            if pruned_count:
                if hasattr(state, "messages"):
                    state.messages = new_messages
                elif isinstance(state, dict):
                    state["messages"] = new_messages

                dtg_context["_drift_fingerprints"] = drift_store
                dtg_context["pruned_tokens_saved_est"] = int(dtg_context.get("pruned_tokens_saved_est") or 0) + tokens_saved_est
                dtg_context["pruned_messages_count"] = int(dtg_context.get("pruned_messages_count") or 0) + pruned_count
        except Exception:
            # Nunca romper el pipeline por poda.
            pass

        total_chars = 0
        for m in messages:
            content = getattr(m, "content", None)
            if content:
                total_chars += len(str(content))
        
        if total_chars / 4 > self.token_threshold:
            if os.getenv("SHREDDER_STDERR", "0") == "1":
                sys.stderr.write(f"✂️ [SHREDDER] Alerta de Contexto: {int(total_chars/4)} tokens.\n")
            task_manifest = getattr(state, "task_manifest", None)
            task_obj = getattr(task_manifest, "objective", None) if task_manifest else None
            if not task_obj and isinstance(state, dict):
                task_obj = state.get("task_manifest", {}).get("objective")
            task_obj = task_obj or "Tarea desconocida"
            
            await bus.publish("CONTEXT_SHREDDED", data={"original_tokens": int(total_chars / 4)})
            if os.getenv("SHREDDER_STDERR", "0") == "1":
                sys.stderr.write("✨ [SHREDDER] Contexto destilado para RTX 3060.\n")
            return True
        return False

shredder = AdvancedContextShredder()
