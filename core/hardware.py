import os
import subprocess
from typing import Optional, Tuple


def _parse_first_int(s: str) -> Optional[int]:
    for token in s.replace(",", " ").split():
        try:
            return int(token)
        except ValueError:
            continue
    return None


def get_gpu_vram_mb() -> Tuple[float, float]:
    """
    Returns (used_mb, total_mb). Falls back to (0.0, 0.0) if unavailable.
    Preference order:
      1) pynvml (NVML)
      2) nvidia-smi query
    """
    # 1) NVML (preferred)
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used_mb = float(mem.used) / (1024.0 * 1024.0)
            total_mb = float(mem.total) / (1024.0 * 1024.0)
            return used_mb, total_mb
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
    except Exception:
        pass

    # 2) nvidia-smi (fallback)
    try:
        env = dict(os.environ)
        env["LC_ALL"] = "C"
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            env=env,
            timeout=2.0,
        ).strip()
        # Example: "123, 6144"
        parts = [p.strip() for p in out.split(",")]
        used = _parse_first_int(parts[0]) if len(parts) > 0 else None
        total = _parse_first_int(parts[1]) if len(parts) > 1 else None
        if used is None or total is None:
            return 0.0, 0.0
        return float(used), float(total)
    except Exception:
        return 0.0, 0.0
