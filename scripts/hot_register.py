"""
AgentOrquestor — Hot Registration Utility v5.0
==============================================
Permite registrar nuevas herramientas en el registry.yaml
desde la línea de comandos o subprocesos.
"""

import sys
import argparse
from pathlib import Path
from core.mission_planner import planner

def main():
    parser = argparse.ArgumentParser(description="Registro de herramientas en caliente.")
    parser.add_argument("--agent", required=True, help="Nombre del agente (ej. LeadDeveloper)")
    parser.add_argument("--tool", required=True, help="Nombre de la herramienta (ej. network_audit)")
    
    args = parser.parse_args()
    
    try:
        planner.register_tool(args.agent, args.tool)
        print(f"✅ Herramienta '{args.tool}' registrada exitosamente para {args.agent}.")
    except Exception as e:
        print(f"❌ Error al registrar herramienta: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
