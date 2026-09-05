"""
Tests for Risk Sentinel — Razorpay Live Test Mode Integration & Gateway
Validates connection management, live key rejection, order creation with manual capture,
checkout signature verification, pre-capture risk evaluation, capture suppression invariants,
zero-fabrication fail-closed boundaries, cross-verification, and the 9-point self-test suite.
"""

import unittest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient

from src.engine.api import app, razorpay_live_service
from src.engine.transaction_store import default_transaction_store

class TestRazorpayLiveIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        default_transaction_store.clear()
        razorpay_live_service.disconnect()

    def tearDown(self):
        razorpay_live_service.disconnect()

    def test_01_connect_rejects_live_keys(self):
        """Security Policy: Rejects rzp_live_ keys immediately."""
        response = self.client.post(
            "/v1/integrations/razorpay/connect",
            json={
                "key_id": "rzp_live_dangerous_key_12345",
                "key_secret": "live_secret_67890"
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Production live keys", response.json()["detail"])

    def test_02_connect_rejects_invalid_key_prefix(self):
        """Rejects keys that do not start with rzp_test_."""
        response = self.client.post(
            "/v1/integrations/razorpay/connect",
            json={
                "key_id": "invalid_prefix_key_123",
                "key_secret": "some_secret"
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("must start with 'rzp_test_'", response.json()["detail"])

    def test_03_get_status_unconnected(self):
        """Verifies status endpoint when disconnected."""
        response = self.client.get("/v1/integrations/razorpay/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("connected", data)
        self.assertIn("mode", data)

    def test_04_create_order_manual_capture(self):
        """Verifies order creation outputs payment_capture: 0 (manual capture mode)."""
        response = self.client.post(
            "/v1/integrations/razorpay/orders",
            json={
                "amount_paise": 50000,
                "currency": "INR",
                "receipt": "rcpt_test_001",
                "notes": {
                    "step": 1,
                    "type": "PAYMENT",
                    "oldbalanceOrg": 10000.0,
                    "oldbalanceDest": 500.0
                }
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["order_id"].startswith("order_"))
        self.assertEqual(data["amount_paise"], 50000)
        self.assertEqual(data["amount_inr"], 500.0)
        self.assertEqual(data["payment_capture"], 0) # Manual capture mode invariant

    def test_05_checkout_signature_tamper_detection(self):
        """Verifies that forged or mismatched checkout signatures are rejected."""
        razorpay_live_service._key_id = "rzp_test_mock_judge_key"
        razorpay_live_service._key_secret = "secret_xyz123"

        response = self.client.post(
            "/v1/integrations/razorpay/checkout/process",
            json={
                "order_id": "order_MOCK_123",
                "payment_id": "pay_MOCK_456",
                "signature": "tampered_signature_deadbeef_0000",
                "amount_paise": 50000
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cryptographic Signature Mismatch", response.json()["detail"])

    def test_06_checkout_process_approved_benign(self):
        """Verifies end-to-end checkout processing for a benign approved payment."""
        order_id = "order_BENIGN_001"
        payment_id = "pay_BENIGN_001"
        secret = "test_secret_pass"
        razorpay_live_service._key_id = "rzp_test_valid_dummy"
        razorpay_live_service._key_secret = secret

        valid_sig = hmac.new(
            secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/v1/integrations/razorpay/checkout/process",
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": valid_sig,
                "amount_paise": 10000,
                "notes": {
                    "step": 1,
                    "type": "PAYMENT",
                    "oldbalanceOrg": 50000.0,
                    "oldbalanceDest": 200.0,
                    "nameOrig": "C_BENIGN_BUYER",
                    "nameDest": "M_TEST_STORE"
                }
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["decision"], "APPROVED")
        self.assertEqual(data["capture_action"], "CAPTURE_CALLED")
        self.assertEqual(data["capture_status"], "CAPTURED")
        self.assertLess(data["risk_score"], 0.70)
        self.assertEqual(len(data["integrity_hash"]), 64)

        # Check TransactionStore persistence
        tx = default_transaction_store.get_by_id(f"tx_{payment_id}")
        self.assertIsNotNone(tx)
        self.assertEqual(tx.decision, "APPROVED")
        self.assertEqual(tx.auto_response_action, "CAPTURE_PERMITTED")

    def test_07_checkout_process_declined_high_risk_drain(self):
        """Verifies that high-risk account drain payments are DECLINED and capture is SUPPRESSED."""
        order_id = "order_DRAIN_001"
        payment_id = "pay_DRAIN_001"
        secret = "test_secret_pass"
        razorpay_live_service._key_id = "rzp_test_valid_dummy"
        razorpay_live_service._key_secret = secret

        valid_sig = hmac.new(
            secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/v1/integrations/razorpay/checkout/process",
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": valid_sig,
                "amount_paise": 50000000, # 500,000 INR full balance drain
                "notes": {
                    "step": 1,
                    "type": "TRANSFER",
                    "oldbalanceOrg": 500000.0,
                    "oldbalanceDest": 0.0,
                    "nameOrig": "C_VICTIM_DRAIN",
                    "nameDest": "M_FRAUD_DEST"
                }
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["decision"], "DECLINED")
        self.assertEqual(data["capture_action"], "CAPTURE_SUPPRESSED")
        self.assertEqual(data["capture_status"], "HELD_DECLINED")
        self.assertGreaterEqual(data["risk_score"], 0.990)

        # Check TransactionStore persistence
        tx = default_transaction_store.get_by_id(f"tx_{payment_id}")
        self.assertIsNotNone(tx)
        self.assertEqual(tx.decision, "DECLINED")
        self.assertEqual(tx.auto_response_action, "CAPTURE_SUPPRESSED")

    def test_08_live_cross_verification_endpoint(self):
        """Tests the cross-verification endpoint comparing local decision vs live state."""
        order_id = "order_VERIFY_001"
        payment_id = "pay_VERIFY_001"
        secret = "test_secret_pass"
        razorpay_live_service._key_id = "rzp_test_valid_dummy"
        razorpay_live_service._key_secret = secret

        valid_sig = hmac.new(
            secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        self.client.post(
            "/v1/integrations/razorpay/checkout/process",
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": valid_sig,
                "amount_paise": 10000,
                "notes": {
                    "step": 1,
                    "type": "PAYMENT",
                    "oldbalanceOrg": 5000.0,
                    "oldbalanceDest": 100.0
                }
            }
        )

        response = self.client.get(f"/v1/integrations/razorpay/verify/{payment_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["payment_id"], payment_id)
        self.assertTrue(data["local_record_found"])
        self.assertEqual(data["local_decision"], "APPROVED")
        self.assertFalse(data["discrepancy_detected"])

    def test_09_self_test_suite_all_pass_and_categorized(self):
        """Tests the 9-point self-test suite endpoint and verifies explicit honest categorization."""
        response = self.client.get("/v1/integrations/razorpay/self-test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["total_tests"], 9)
        self.assertEqual(data["passed_tests"], 9)
        self.assertEqual(len(data["tests"]), 9)

        valid_categories = {"LIVE_PROVEN", "CONTRACT_PROVEN", "LOCAL_POLICY_INVARIANT_PROVEN", "NOT_EXECUTED"}
        for t in data["tests"]:
            self.assertIn("category", t)
            self.assertIn(t["category"], valid_categories)

        # Step 6 must be CONTRACT_PROVEN with readiness details
        step6 = next(t for t in data["tests"] if t["step"] == 6)
        self.assertEqual(step6["category"], "CONTRACT_PROVEN")
        self.assertIn("NOT_EXECUTED until", step6["details"])

        # Step 7 must be LOCAL_POLICY_INVARIANT_PROVEN
        step7 = next(t for t in data["tests"] if t["step"] == 7)
        self.assertEqual(step7["category"], "LOCAL_POLICY_INVARIANT_PROVEN")

    def test_10_disconnect_endpoint(self):
        """Tests clearing active credentials from server memory."""
        razorpay_live_service._key_id = "rzp_test_temp"
        razorpay_live_service._key_secret = "temp_secret"
        
        response = self.client.post("/v1/integrations/razorpay/disconnect")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["connected"])
        self.assertIsNone(data["key_id_masked"])
        self.assertIsNone(razorpay_live_service._key_id)
        self.assertIsNone(razorpay_live_service._key_secret)

    def test_11_payment_retrieval_failure_fails_closed_zero_fabrication(self):
        """CRITICAL FIX: When Razorpay API payment retrieval fails, FAIL CLOSED and NEVER fabricate an authorized payment."""
        order_id = "order_FAIL_RETRIEVAL_001"
        payment_id = "pay_REAL_NONEXISTENT_99999" # Not a mock/contract ID -> will try live API
        secret = "secret_test_failclosed"
        
        # Configure test credentials
        razorpay_live_service._key_id = "rzp_test_real_prefix_test"
        razorpay_live_service._key_secret = secret

        valid_sig = hmac.new(
            secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/v1/integrations/razorpay/checkout/process",
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": valid_sig,
                "amount_paise": 50000,
                "notes": {
                    "step": 1,
                    "type": "PAYMENT",
                    "oldbalanceOrg": 10000.0,
                    "oldbalanceDest": 200.0
                }
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Invariants: Must fail closed, suppress capture, never fabricate authorized state
        self.assertEqual(data["decision"], "NOT_EVALUATED")
        self.assertEqual(data["action"], "HOLD_NO_CAPTURE")
        self.assertEqual(data["capture_action"], "CAPTURE_SUPPRESSED")
        self.assertEqual(data["capture_status"], "HELD_PAYMENT_RETRIEVAL_FAILED")
        self.assertEqual(data["risk_evaluation_status"], "PAYMENT_RETRIEVAL_FAILED")
        self.assertTrue(data["capture_api_response"].get("fail_closed"))

        # Verify transaction store also recorded HELD_PAYMENT_RETRIEVAL_FAILED
        tx = default_transaction_store.get_by_id(f"tx_{payment_id}")
        self.assertIsNotNone(tx)
        self.assertEqual(tx.auto_response_status, "HELD_PAYMENT_RETRIEVAL_FAILED")
        self.assertEqual(tx.auto_response_action, "CAPTURE_SUPPRESSED")

    def test_12_insufficient_context_notes_fails_closed(self):
        """Verifies that missing pre-transaction balance features strictly fails closed (zero feature fabrication)."""
        order_id = "order_NOCONTEXT_001"
        payment_id = "pay_CONTRACT_NOCONTEXT_001"
        secret = "test_secret_pass"
        razorpay_live_service._key_id = "rzp_test_valid_dummy"
        razorpay_live_service._key_secret = secret

        valid_sig = hmac.new(
            secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/v1/integrations/razorpay/checkout/process",
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": valid_sig,
                "amount_paise": 10000,
                "notes": {} # Empty notes -> missing required banking features
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["decision"], "NOT_EVALUATED")
        self.assertEqual(data["action"], "HOLD_NO_CAPTURE")
        self.assertEqual(data["capture_action"], "CAPTURE_SUPPRESSED")
        self.assertEqual(data["capture_status"], "HELD_INSUFFICIENT_CONTEXT")
        self.assertEqual(data["risk_evaluation_status"], "INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION")

if __name__ == "__main__":
    unittest.main()
