import unittest
from agents.skills.git_autocommit.schema import GitAutocommitContract
from pydantic import ValidationError

class TestGitAutocommitSchema(unittest.TestCase):
    def test_valid_contract_instantiation(self):
        valid_payload = {
            "skill_id": "8fa802ca-6af3-4c91-9e73-b6c867a5b3a2",
            "intent_context": "update core memory architecture",
            "payload": {
                "commit_message": "refactor: optimización de VRAM a 12%",
                "push_remote": False
            },
            "zero_trust_telemetry": {
                "ebpf_trace_id": "ebpf_ring_x9102",
                "z3_invariant_verified": True
            }
        }
        
        contract = GitAutocommitContract(**valid_payload)
        self.assertEqual(contract.skill_id, "8fa802ca-6af3-4c91-9e73-b6c867a5b3a2")
        self.assertTrue(contract.zero_trust_telemetry.z3_invariant_verified)
        self.assertFalse(contract.payload.push_remote)

    def test_invalid_telemetry_blocked(self):
        invalid_payload = {
            "skill_id": "123",
            "intent_context": "bad request",
            "payload": {},
            "zero_trust_telemetry": {
                "ebpf_trace_id": "missing_z3"
                # Missing z3_invariant_verified (Mandatory by Architecture)
            }
        }
        
        with self.assertRaises(ValidationError):
            GitAutocommitContract(**invalid_payload)

if __name__ == '__main__':
    unittest.main()
