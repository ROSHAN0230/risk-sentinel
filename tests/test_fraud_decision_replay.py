"""
Risk Sentinel — Phase 2 Fraud Decision Replay Test Suite
Tests for:
1. Exact drain scenario (RC_EXACT_BALANCE_DRAIN -> DECLINED)
2. Reduced amount sensitivity (decision transition)
3. Applicable channel-path behavior (PAYMENT fast-path bypass)
4. Stateful context sensitivity (mule fan-in counts in sandbox)
5. Economic sensitivity (alpha scaling and disclaimer)
6. Zero production state store mutation (verified across 50 runs)
7. Zero audit ledger pollution (events list unchanged)
8. Immutable production thresholds (0.990 / 0.900)
9. Frozen artifact SHA-256 hashes (all 9 files match byte-for-byte)
10. FastAPI POST /v1/replay/evaluate contract test
11. Malformed / invalid inputs rejected safely
12. Sandbox state isolation across repeated replays
"""

import unittest
import hashlib
from fastapi.testclient import TestClient

from src.engine.decision_engine import RiskDecisionEngine
from src.engine.analytics.replay_service import ReplayService, ReplayRequest, SandboxContext
from src.engine.api import app, engine as prod_engine

class TestFraudDecisionReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = ReplayService(prod_engine=prod_engine)
        cls.client = TestClient(app)

    def test_01_exact_drain_replays_decline(self):
        """100% balance drain replay -> score >= 0.990 -> DECLINED + RC_EXACT_BALANCE_DRAIN."""
        req = ReplayRequest(
            baseline_fixture_id="DEMO-03",
            step=452,
            type="TRANSFER",
            amount=284100.50,
            nameOrig="C_REPLAY_VICTIM",
            oldbalanceOrg=284100.50,
            nameDest="C_REPLAY_MULE",
            oldbalanceDest=0.0,
            alpha=0.010
        )
        res = self.service.evaluate_replay(req)
        self.assertEqual(res.replayed_evaluation.decision, "DECLINED")
        self.assertGreaterEqual(res.replayed_evaluation.operating_score, 0.990)
        self.assertEqual(res.replayed_evaluation.primary_reason_code, "RC_EXACT_BALANCE_DRAIN")
        self.assertEqual(res.economic_impact.decision_outcome, "DECLINED")
        self.assertGreater(res.economic_impact.hypothetical_friction_cost, 0.0)

    def test_02_reduced_amount_shifts_decision(self):
        """Lowering amount to a minor fraction of balance shifts decision from DECLINED to APPROVED."""
        req = ReplayRequest(
            baseline_fixture_id="DEMO-03",
            step=452,
            type="TRANSFER",
            amount=50.00,  # Only 50 out of 284,100 balance
            nameOrig="C_REPLAY_VICTIM",
            oldbalanceOrg=284100.50,
            nameDest="C_REPLAY_MULE",
            oldbalanceDest=0.0,
            alpha=0.010
        )
        res = self.service.evaluate_replay(req)
        self.assertEqual(res.replayed_evaluation.decision, "APPROVED")
        self.assertLess(res.replayed_evaluation.operating_score, 0.900)
        self.assertIsNotNone(res.deltas)
        self.assertTrue(res.deltas.decision_changed)
        self.assertEqual(res.deltas.baseline_decision, "DECLINED")
        self.assertEqual(res.deltas.replay_decision, "APPROVED")

    def test_03_channel_bypass_replay(self):
        """Replaying as PAYMENT triggers fast-path bypass with minimal score."""
        req = ReplayRequest(
            step=450,
            type="PAYMENT",
            amount=1000.00,
            nameOrig="C_REPLAY_SENDER",
            oldbalanceOrg=5000.00,
            nameDest="M_REPLAY_MERCHANT",
            oldbalanceDest=0.0,
            alpha=0.010
        )
        res = self.service.evaluate_replay(req)
        self.assertEqual(res.replayed_evaluation.decision, "APPROVED")
        self.assertEqual(res.replayed_evaluation.primary_reason_code, "RC_BENIGN_BASELINE")
        self.assertLessEqual(res.replayed_evaluation.operating_score, 0.01)

    def test_04_stateful_context_sensitivity(self):
        """Seeding high destination fan-in count in sandbox context increases stateful feature."""
        req = ReplayRequest(
            step=452,
            type="TRANSFER",
            amount=50000.00,
            nameOrig="C_SENDER_MULE_TEST",
            oldbalanceOrg=100000.00,
            nameDest="C_HIGH_FANIN_DEST",
            oldbalanceDest=0.0,
            sandbox_context=SandboxContext(dest_unique_orig_cnt=15),
            alpha=0.010
        )
        res = self.service.evaluate_replay(req)
        self.assertEqual(res.replayed_evaluation.features["dest_unique_orig_cnt"], 15.0)

    def test_05_economic_sensitivity_and_disclaimer(self):
        """Validates that friction cost scales with alpha and carries explicit disclaimer."""
        amount = 100000.00
        # Replay DECLINE at alpha = 0.01
        res1 = self.service.evaluate_replay(ReplayRequest(
            step=452, type="TRANSFER", amount=amount, oldbalanceOrg=amount,
            nameOrig="C_VICTIM", nameDest="C_DEST", alpha=0.010
        ))
        self.assertEqual(res1.economic_impact.hypothetical_friction_cost, 1000.00) # 1% of 100,000
        self.assertIn("Analytical scenario sensitivity", res1.economic_impact.disclaimer)

        # Replay DECLINE at alpha = 0.04
        res2 = self.service.evaluate_replay(ReplayRequest(
            step=452, type="TRANSFER", amount=amount, oldbalanceOrg=amount,
            nameOrig="C_VICTIM", nameDest="C_DEST", alpha=0.040
        ))
        self.assertEqual(res2.economic_impact.hypothetical_friction_cost, 4000.00) # 4% of 100,000

    def test_06_zero_production_state_store_mutation(self):
        """50 repeated replays must NOT alter the production state store."""
        initial_sender_keys = set(prod_engine.state_store.sender_state.keys())
        initial_dest_keys = set(prod_engine.state_store.dest_state.keys())

        for i in range(50):
            self.service.evaluate_replay(ReplayRequest(
                step=450 + i,
                type="TRANSFER",
                amount=float(100 + i),
                oldbalanceOrg=float(500 + i),
                nameOrig=f"C_ISOLATION_TEST_SENDER_{i}",
                nameDest=f"C_ISOLATION_TEST_DEST_{i}",
                alpha=0.010
            ))

        final_sender_keys = set(prod_engine.state_store.sender_state.keys())
        final_dest_keys = set(prod_engine.state_store.dest_state.keys())

        self.assertEqual(initial_sender_keys, final_sender_keys)
        self.assertEqual(initial_dest_keys, final_dest_keys)

    def test_07_zero_audit_ledger_pollution(self):
        """Replay evaluations must NOT write events to the production audit ledger."""
        initial_audit_count = len(prod_engine.audit_logger.events)

        for i in range(25):
            self.service.evaluate_replay(ReplayRequest(
                step=450,
                type="TRANSFER",
                amount=284100.50,
                oldbalanceOrg=284100.50,
                nameOrig="C_AUDIT_TEST_SENDER",
                nameDest="C_AUDIT_TEST_DEST",
                alpha=0.020
            ))

        final_audit_count = len(prod_engine.audit_logger.events)
        self.assertEqual(initial_audit_count, final_audit_count)

    def test_08_immutable_production_thresholds(self):
        """Production thresholds remain locked at 0.990 and 0.900."""
        self.assertEqual(prod_engine.operating_threshold, 0.990)
        self.assertEqual(prod_engine.policy_engine.threshold_high, 0.990)
        self.assertEqual(prod_engine.policy_engine.threshold_medium, 0.900)

    def test_09_all_9_frozen_hashes_match(self):
        """All 9 frozen core engine artifacts remain 100% byte-for-byte identical."""
        expected = {
            'model_b_stateful_hgb.joblib': ('src/engine/artifacts/model_b_stateful_hgb.joblib', '5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735'),
            'model_a_causal_hgb.joblib': ('src/engine/artifacts/model_a_causal_hgb.joblib', 'ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373'),
            'policy_engine.py': ('src/engine/policy_engine.py', 'b61ab343af0e5aa84726db1d96700b89b8e22b88a597f73c97b8320b430b9b5e'),
            'decision_engine.py': ('src/engine/decision_engine.py', '1b5f1615f90548fa5eba94231e207d43d3e0bf7a6d68d47b802a56daaa747a4f'),
            'feature_pipeline.py': ('src/engine/feature_pipeline.py', '41b315ed0eaff96321d7dfabab72f5fdd1a254a39604445500d545bc55a7b993'),
            'model_manager.py': ('src/engine/model_manager.py', 'e2400085415e93554e480d8ff4f78fe22852c007fc5926fc27da0352d5f6899a'),
            'schemas.py': ('src/engine/schemas.py', 'de16b6bba9d2b235611adf52272ff033cb40eafff6ce92c2b7de56725ff093bf'),
            'audit_logger.py': ('src/engine/audit_logger.py', '044951b6a014a07cd48179cd9d5388373ddd2b4e0dc980934db1d980e4a68afb'),
            'state_store.py': ('src/engine/state_store.py', 'f7f6615a0277bb11631fe4dbc0be5ddde26a1c28889eff6827243946b2b70d35')
        }
        for name, (path, exp_hash) in expected.items():
            with open(path, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(actual_hash, exp_hash, f"Hash mismatch in frozen core: {name}")

    def test_10_api_replay_endpoint_contract(self):
        """FastAPI POST /v1/replay/evaluate returns 200 with full ReplayResponse structure."""
        payload = {
            "baseline_fixture_id": "DEMO-03",
            "step": 452,
            "type": "TRANSFER",
            "amount": 284100.50,
            "nameOrig": "C_VICTIM_03",
            "oldbalanceOrg": 284100.50,
            "nameDest": "C_MULE_03",
            "oldbalanceDest": 0.0,
            "alpha": 0.015
        }
        resp = self.client.post("/v1/replay/evaluate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("replay_id", data)
        self.assertEqual(data["provenance"], "EXPLORATORY_REPLAY — ZERO PRODUCTION MUTATION")
        self.assertEqual(data["replayed_evaluation"]["decision"], "DECLINED")
        self.assertEqual(data["replayed_evaluation"]["primary_reason_code"], "RC_EXACT_BALANCE_DRAIN")
        self.assertIn("economic_impact", data)
        self.assertEqual(data["economic_impact"]["alpha"], 0.015)

    def test_11_malformed_inputs_rejected(self):
        """Zero amount or negative balance returns schema validation error."""
        bad_payload = {
            "step": 450,
            "type": "TRANSFER",
            "amount": -500.0, # Negative amount
            "oldbalanceOrg": 1000.0
        }
        resp = self.client.post("/v1/replay/evaluate", json=bad_payload)
        self.assertEqual(resp.status_code, 422)

    def test_12_sandbox_state_isolation_between_replays(self):
        """Replay A modifying sandbox context must not affect Replay B."""
        # Replay A with fan-in count = 20
        res_a = self.service.evaluate_replay(ReplayRequest(
            step=450, type="TRANSFER", amount=1000.0, oldbalanceOrg=2000.0,
            nameDest="C_SHARED_DEST", sandbox_context=SandboxContext(dest_unique_orig_cnt=20)
        ))
        self.assertEqual(res_a.replayed_evaluation.features["dest_unique_orig_cnt"], 20.0)

        # Replay B without fan-in count override on the same destination
        res_b = self.service.evaluate_replay(ReplayRequest(
            step=450, type="TRANSFER", amount=1000.0, oldbalanceOrg=2000.0,
            nameDest="C_SHARED_DEST"
        ))
        self.assertEqual(res_b.replayed_evaluation.features["dest_unique_orig_cnt"], 0.0)

if __name__ == '__main__':
    unittest.main()
