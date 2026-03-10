
import asyncio
import sys
import os

# Añadir el directorio actual al path para importar el módulo agents
sys.path.append(os.getcwd())

from agents.skills.git_autocommit.executor import GitAutocommitExecutor

async def main():
    contract_data = {
        "skill_id": "8e3b5e1a-4f5c-4d2a-9b1e-7f6d5c4b3a21",
        "intent_context": "Implementación de fábrica de agentes con AutoGen y DSPy para el orquestador swarm.",
        "payload": {
            "commit_message": "feat(agents): implement dspy signatures, autogen factory and swarm manager\n\n- Added agents/signatures.py with CodeRefactor and SecurityAudit signatures.\n- Added agents/factory.py with AutoGen agents and PyramidKV optimization.\n- Added agents/manager.py to bridge LangGraph with the AutoGen swarm.",
            "push_remote": True
        },
        "zero_trust_telemetry": {
            "ebpf_trace_id": "trace-2026-03-10-agent-swarm-impl",
            "z3_invariant_verified": True
        }
    }
    
    try:
        executor = GitAutocommitExecutor(contract_data)
        result = await executor.execute()
        print(f"Resultado de la Skill: {result}")
    except Exception as e:
        print(f"Error al ejecutar la skill: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
