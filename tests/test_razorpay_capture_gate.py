"""
Risk Sentinel — Phase 1 Razorpay Capture Gate Test Suite
Tests for:
1. Authorized benign payment captures
2. Authorized high-risk drain suppresses capture (HOLD)
3. Non-authorized payment rejected (no capture)
4. Missing context fails closed (no capture)
5. Idempotent duplicate processing
6. Live vs Simulated mode transparency
7. Rejection of production non-test keys (rzp_live_...)
8. SHA-256 block hash integrity chaining
9. All 9 frozen core hashes match byte-for-byte
10. Production thresholds intact (0.990 / 0.900)
11. Capture API failure handling
12. Contact PII masking
"""

import unittest
import hashlib
from unittest.mock import patch, MagicMock

from src.engine.decision_engine import RiskDecisionEngine
from src.engine.integrations.razorpay_capture_gate import (
    RazorpayCaptureGate,
    RazorpayCaptureRequest,
    CaptureGateResult,
    mask_contact
)

class TestRazorpayCaptureGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RiskDecisionEngine()
        cls.gate = RazorpayCaptureGate(engine=cls.engine)

    def test_01_authorized_payment_benign_captures(self):
        """Benign payment (PAYMENT channel) -> APPROVED -> Capture Called -> CAPTURED."""
        req = RazorpayCaptureRequest(
            payment_id="pay_test_benign_001",
            order_id="order_test_benign_001",
            amount_paise=8450,  # 84.50 INR
            currency="INR",
            status="authorized",
            method="upi",
            contact="9876543210",
            notes={
                "step": "450",
                "type": "PAYMENT",
                "oldbalanceOrg": "10000.00",
                "oldbalanceDest": "50000.00",
                "nameOrig": "C_BENIGN_SENDER",
                "nameDest": "M_BENIGN_MERCHANT"
            }
        )
        res = self.gate.evaluate_and_capture(req)
        self.assertEqual(res.payment_status_before, "authorized")
        self.assertEqual(res.decision, "APPROVED")
        self.assertEqual(res.capture_action, "CAPTURE_CALLED")
        self.assertEqual(res.capture_status, "CAPTURED")
        self.assertFalse(res.is_duplicate)
        self.assertIsNotNone(res.integrity_hash)

    def test_02_authorized_payment_drain_holds(self):
        """High-risk 100% balance drain -> DECLINED -> Capture Suppressed -> HELD_DECLINED."""
        req = RazorpayCaptureRequest(
            payment_id="pay_test_drain_002",
            order_id="order_test_drain_002",
            amount_paise=28410050,  # 284,100.50 INR
            currency="INR",
            status="authorized",
            method="upi",
            notes={
                "step": "452",
                "type": "TRANSFER",
                "oldbalanceOrg": "284100.50",
                "oldbalanceDest": "0.00",
                "nameOrig": "C_VICTIM_DRAIN",
                "nameDest": "C_MULE_DRAIN"
            }
        )
        res = self.gate.evaluate_and_capture(req)
        self.assertEqual(res.payment_status_before, "authorized")
        self.assertEqual(res.decision, "DECLINED")
        self.assertEqual(res.capture_action, "CAPTURE_SUPPRESSED")
        self.assertEqual(res.capture_status, "HELD_DECLINED")
        self.assertGreaterEqual(res.risk_score, 0.990)
        self.assertEqual(res.primary_reason_code, "RC_EXACT_BALANCE_DRAIN")

    def test_03_non_authorized_payment_rejected(self):
        """Payments with status != 'authorized' are rejected without evaluation or capture."""
        for bad_status in ["failed", "captured", "created", "refunded"]:
            req = RazorpayCaptureRequest(
                payment_id=f"pay_test_{bad_status}_003",
                amount_paise=50000,
                status=bad_status,
                notes={"step": "1", "type": "PAYMENT", "oldbalanceOrg": "1000", "oldbalanceDest": "0"}
            )
            res = self.gate.evaluate_and_capture(req)
            self.assertEqual(res.payment_status_before, bad_status)
            self.assertEqual(res.risk_evaluation_status, "NON_AUTHORIZED_PAYMENT")
            self.assertEqual(res.capture_action, "CAPTURE_SUPPRESSED")
            self.assertEqual(res.capture_status, "HELD_NON_AUTHORIZED")

    def test_04_missing_risk_context_fails_closed(self):
        """Raw payment without banking balance notes fails closed without capture."""
        req = RazorpayCaptureRequest(
            payment_id="pay_test_raw_004",
            amount_paise=50000,
            status="authorized",
            notes={}  # Missing step, type, oldbalanceOrg, oldbalanceDest
        )
        res = self.gate.evaluate_and_capture(req)
        self.assertEqual(res.risk_evaluation_status, "INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION")
        self.assertEqual(res.decision, "NOT_EVALUATED")
        self.assertEqual(res.capture_action, "CAPTURE_SUPPRESSED")
        self.assertEqual(res.capture_status, "HELD_INSUFFICIENT_CONTEXT")

    def test_05_idempotent_duplicate_prevention(self):
        """Duplicate request returns cached decision with is_duplicate=True, no double capture."""
        req = RazorpayCaptureRequest(
            payment_id="pay_test_dup_005",
            amount_paise=10000,
            status="authorized",
            notes={"step": "450", "type": "PAYMENT", "oldbalanceOrg": "5000", "oldbalanceDest": "1000"}
        )
        res1 = self.gate.evaluate_and_capture(req)
        self.assertFalse(res1.is_duplicate)
        self.assertEqual(res1.capture_status, "CAPTURED")

        res2 = self.gate.evaluate_and_capture(req)
        self.assertTrue(res2.is_duplicate)
        self.assertEqual(res2.gate_event_id, res1.gate_event_id)
        self.assertEqual(res2.capture_status, res1.capture_status)

    def test_06_live_vs_simulated_mode_transparency(self):
        """Verifies explicit labeling of execution mode."""
        # Unconfigured keys -> SIMULATED_CONTRACT_TEST_MODE
        gate_sim = RazorpayCaptureGate(engine=self.engine, key_id="", key_secret="")
        self.assertFalse(gate_sim.has_live_credentials)
        req = RazorpayCaptureRequest(
            payment_id="pay_test_sim_006",
            amount_paise=5000,
            status="authorized",
            notes={"step": "1", "type": "PAYMENT", "oldbalanceOrg": "1000", "oldbalanceDest": "0"}
        )
        res_sim = gate_sim.evaluate_and_capture(req)
        self.assertEqual(res_sim.execution_mode, "SIMULATED_CONTRACT_TEST_MODE")
        self.assertEqual(res_sim.provenance, "RAZORPAY_COMPATIBLE_TEST_MODE")

        # Configured test keys -> LIVE_RAZORPAY_TEST_MODE
        gate_live = RazorpayCaptureGate(engine=self.engine, key_id="rzp_test_abc123", key_secret="secret_abc123")
        self.assertTrue(gate_live.has_live_credentials)

    def test_07_rejection_of_production_keys(self):
        """Live-mode keys (e.g. rzp_live_...) must be rejected to ensure Test Mode safety."""
        with self.assertRaises(ValueError) as ctx:
            RazorpayCaptureGate(engine=self.engine, key_id="rzp_live_secretkey", key_secret="secret")
        self.assertIn("operates exclusively in Razorpay Test Mode", str(ctx.exception))

    def test_08_immutable_chained_hash(self):
        """Successive gate decisions produce chained SHA-256 hashes."""
        req1 = RazorpayCaptureRequest(
            payment_id="pay_test_chain_008a",
            amount_paise=1000,
            status="authorized",
            notes={"step": "1", "type": "PAYMENT", "oldbalanceOrg": "500", "oldbalanceDest": "0"}
        )
        res1 = self.gate.evaluate_and_capture(req1)
        self.assertEqual(len(res1.integrity_hash), 64)

        req2 = RazorpayCaptureRequest(
            payment_id="pay_test_chain_008b",
            amount_paise=2000,
            status="authorized",
            notes={"step": "1", "type": "PAYMENT", "oldbalanceOrg": "500", "oldbalanceDest": "0"}
        )
        res2 = self.gate.evaluate_and_capture(req2)
        self.assertEqual(len(res2.integrity_hash), 64)
        self.assertNotEqual(res1.integrity_hash, res2.integrity_hash)

    def test_09_all_9_frozen_hashes_match(self):
        """Guarantees that Phase 1 implementation leaves all 9 core engine files 100% untouched."""
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

    def test_10_production_thresholds_intact(self):
        """Production operating thresholds remain locked at 0.990 and 0.900."""
        self.assertEqual(self.engine.operating_threshold, 0.990)
        self.assertEqual(self.engine.policy_engine.threshold_high, 0.990)
        self.assertEqual(self.engine.policy_engine.threshold_medium, 0.900)

    def test_11_capture_api_failure_handling(self):
        """Capture API failure is handled cleanly, returning CAPTURE_FAILED."""
        gate = RazorpayCaptureGate(engine=self.engine)
        # Mock _call_razorpay_capture_api to simulate gateway timeout/error
        with patch.object(gate, '_call_razorpay_capture_api', return_value=(False, {"http_code": 504, "error": "Gateway Timeout"})):
            req = RazorpayCaptureRequest(
                payment_id="pay_test_timeout_011",
                amount_paise=5000,
                status="authorized",
                notes={"step": "1", "type": "PAYMENT", "oldbalanceOrg": "1000", "oldbalanceDest": "0"}
            )
            res = gate.evaluate_and_capture(req)
            self.assertEqual(res.capture_action, "CAPTURE_FAILED")
            self.assertEqual(res.capture_status, "HELD_CAPTURE_API_ERROR")

    def test_12_masking_of_contact_pii(self):
        """Contact phone numbers are masked to protect customer PII."""
        self.assertIsNone(mask_contact(None))
        self.assertEqual(mask_contact(""), None)
        self.assertEqual(mask_contact("1234"), "****")
        self.assertEqual(mask_contact("9876543210"), "98******10")

    def test_13_api_evaluate_and_capture_endpoint(self):
        """FastAPI POST /v1/gate/evaluate-and-capture returns 200 with CaptureGateResult."""
        from fastapi.testclient import TestClient
        from src.engine.api import app
        client = TestClient(app)
        payload = {
            "payment_id": "pay_test_api_013",
            "order_id": "order_test_api_013",
            "amount_paise": 10000,
            "currency": "INR",
            "status": "authorized",
            "method": "upi",
            "notes": {
                "step": "450",
                "type": "PAYMENT",
                "oldbalanceOrg": "10000.00",
                "oldbalanceDest": "5000.00"
            }
        }
        resp = client.post("/v1/gate/evaluate-and-capture", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["payment_id"], "pay_test_api_013")
        self.assertEqual(data["decision"], "APPROVED")
        self.assertEqual(data["capture_status"], "CAPTURED")

    def test_14_api_gate_events_endpoint(self):
        """FastAPI GET /v1/gate/events returns the list of recent gate events."""
        from fastapi.testclient import TestClient
        from src.engine.api import app
        client = TestClient(app)
        resp = client.get("/v1/gate/events?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

if __name__ == '__main__':
    unittest.main()

