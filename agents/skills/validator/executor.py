import os
import subprocess
import sys
import time
import asyncio
from core.event_bus import bus
from core.telemetry import telemetry

class PostTaskValidator:
    """
    Skill de Autodiagnóstico (Fase 5).
    Verifica la integridad del sistema tras cada cambio estructural.
    """
    async def _validate_eventbus_throughput(self, target_eps: float = 500.0) -> tuple[bool, dict]:
        """
        Certifica que el EventBus (con persistencia) mantiene >= target_eps.
        """
        from core.event_bus import bus as event_bus

        async def _noop(_evt):
            return None

        # Subscribe once; duplicate subscriptions are harmless but we avoid churn.
        event_bus.subscribe("PERF_EVENT", _noop)

        prev_stderr = os.getenv("EVENTBUS_STDERR")
        os.environ["EVENTBUS_STDERR"] = "0"
        try:
            n = 1000
            payload = {"p": 1}
            t0 = time.perf_counter()
            await asyncio.gather(
                *[
                    event_bus.publish("PERF_EVENT", data=payload, task_id="perf", correlation_id=str(i))
                    for i in range(n)
                ]
            )
            dt = max(time.perf_counter() - t0, 1e-9)
            eps = float(n) / dt
            ok = eps >= float(target_eps)
            return ok, {"events": n, "elapsed_s": round(dt, 4), "events_per_s": round(eps, 2), "target_eps": target_eps}
        finally:
            if prev_stderr is None:
                os.environ.pop("EVENTBUS_STDERR", None)
            else:
                os.environ["EVENTBUS_STDERR"] = prev_stderr

    async def validate_system(self, file_paths: list):
        prev_eventbus_stderr = os.getenv("EVENTBUS_STDERR")
        os.environ["EVENTBUS_STDERR"] = "0"
        telemetry.info("🔍 [VALIDATOR] Iniciando autodiagnóstico de integridad...")
        
        errors = []
        for file in file_paths:
            if file.endswith(".py") and os.path.exists(file):
                # 1. Chequeo de Sintaxis
                env = dict(os.environ)
                env["PYTHONPYCACHEPREFIX"] = "/tmp/pycache"
                result = subprocess.run(["python3", "-B", "-m", "py_compile", file], capture_output=True, env=env, text=True)
                if result.returncode != 0:
                    errors.append(f"Syntax error in {file}: {result.stderr}")
        
        # 2. Chequeo de Importación del Core
        try:
            import core.telemetry as _telemetry_mod
            import core.event_bus as _event_bus_mod
            telemetry.info("✅ [VALIDATOR] Core operacional (Imports OK)")
        except Exception as e:
            errors.append(f"Core breakdown: {str(e)}")

        # 3. Certificación de Throughput (Swarm Immunity)
        try:
            ok, perf = await self._validate_eventbus_throughput(target_eps=500.0)
            if ok:
                telemetry.info(f"⚡ [VALIDATOR] EventBus throughput OK: {perf}")
                await bus.publish("EVENTBUS_THROUGHPUT_OK", data=perf)
            else:
                errors.append(f"EventBus throughput below target: {perf}")
        except Exception as e:
            errors.append(f"EventBus throughput check failed: {str(e)}")
            
        if not errors:
            telemetry.info("🎊 [VALIDATOR] Sistema íntegro. Cambio verificado con éxito.")
            await bus.publish("SYSTEM_VALIDATED", data={"status": "CLEAN"})
            ok = True
        else:
            telemetry.error(f"❌ [VALIDATOR] Fallos detectados: {errors}")
            await bus.publish("SYSTEM_VALIDATION_FAILED", data={"errors": errors})
            ok = False

        if prev_eventbus_stderr is None:
            os.environ.pop("EVENTBUS_STDERR", None)
        else:
            os.environ["EVENTBUS_STDERR"] = prev_eventbus_stderr
        return ok

executor = PostTaskValidator()
