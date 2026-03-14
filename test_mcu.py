import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.metabolic_governor import mcu
from core.telemetry import telemetry

print("Iniciando prueba de MCU...")
try:
    health = mcu.check_health("test_mission")
    print(f"Health check: {health}")
    mcu.record_consumption("test_mission", "Tester", "llama-3.1-8b-instant", 100, 50)
    print("Consumo registrado con éxito.")
    health_after = mcu.check_health("test_mission")
    print(f"Health after: {health_after}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
