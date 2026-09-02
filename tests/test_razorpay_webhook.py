"""
Risk Sentinel — Phase P0 Razorpay Test Mode Webhook Test Suite
Validates signature security, idempotency, model readiness boundaries, zero-fabrication guarantees,
enriched context evaluation, and audit chaining using standard unittest.
"""

import os
import sys
import hmac
import hashlib
import json
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.api import app, webhook_adapter
from src.engine.schemas import EvaluateRequest

TEST_SECRET = "rzp_webhook_secret_test_key_12345"

class TestRazorpayWebhook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        """Reset adapter state before each test."""
        webhook_adapter.webhook_secret = TEST_SECRET
        webhook_adapter.processed_events.clear()
        webhook_adapter.event_buffer.clear()
        webhook_adapter._last_event_hash = "0" * 64

    def compute_signature(self, payload_bytes: bytes, secret: str = TEST_SECRET) -> str:
        return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def make_sample_payload(
        self,
        payment_id: str = "pay_test_001",
        amount_paise: int = 250000,
        event_type: str = "payment.authorized",
        notes: dict = None
    ) -> dict:
        return {
            "entity": "event",
            "account_id": "acc_razorpay_merchant_01",
            "event": event_type,
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "amount": amount_paise,
                        "currency": "INR",
                        "status": "authorized",
                        "method": "upi",
                        "vpa": "customer@okhdfcbank",
                        "email": "customer@example.com",
                        "contact": "+919876543210",
                        "notes": notes or {},
                        "created_at": 1693651200
                    }
                }
            },
            "created_at": 1693651200
        }

    # 1. Valid Webhook Accepted
    def test_01_valid_webhook_accepted(self):
        payload = self.make_sample_payload(payment_id="pay_valid_001")
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp = self.client.post(
            "/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["source"], "RAZORPAY_TEST_MODE")
        self.assertEqual(data["payment_id"], "pay_valid_001")
        self.assertEqual(data["amount_inr"], 2500.00)
        self.assertEqual(data["currency"], "INR")
        self.assertEqual(data["method"], "upi")
        self.assertEqual(data["customer_contact_masked"], "+9******10")
        self.assertNotEqual(data["integrity_hash"], "0" * 64)

    # 2. Invalid Signature Rejected
    def test_02_invalid_signature_rejected(self):
        payload = self.make_sample_payload(payment_id="pay_sig_fail")
        raw_body = json.dumps(payload).encode("utf-8")
        fake_sig = "invalid_hmac_signature_hex_digest_00000000000000000000000000000000"

        resp = self.client.post(
            "/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": fake_sig}
        )
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data["evaluation_status"], "REJECTED_INVALID_SIGNATURE")

    # 3. Malformed Payload Rejected
    def test_03_malformed_payload_rejected(self):
        raw_body = b"not a json object"
        sig = self.compute_signature(raw_body)

        resp = self.client.post(
            "/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
        )
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data["evaluation_status"], "REJECTED_MALFORMED_PAYLOAD")

    # 4. Duplicate Event is Idempotent
    def test_04_duplicate_event_is_idempotent(self):
        payload = self.make_sample_payload(payment_id="pay_idem_001")
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp1 = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertFalse(data1["is_duplicate"])

        resp2 = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2["is_duplicate"])
        self.assertEqual(data2["event_id"], data1["event_id"])
        self.assertEqual(data2["integrity_hash"], data1["integrity_hash"])

    # 5. Missing Banking Features Produces EVENT_RECEIVED + INSUFFICIENT_FEATURES
    def test_05_raw_payment_missing_banking_features(self):
        payload = self.make_sample_payload(payment_id="pay_raw_gateway_001")
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["evaluation_status"], "INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION")
        self.assertIn("oldbalanceOrg", data["missing_features"])
        self.assertIn("oldbalanceDest", data["missing_features"])
        self.assertIn("step", data["missing_features"])
        self.assertIn("banking-balance context required", data["readiness_reason"])
        self.assertIsNone(data["risk_score"])
        self.assertIsNone(data["decision"])

    # 6. No Fabricated Feature Values Appear
    def test_06_no_fabricated_feature_values(self):
        payload = self.make_sample_payload(payment_id="pay_purity_001")
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        data = resp.json()
        self.assertIsNone(data["risk_score"])
        self.assertIsNone(data["decision"])
        self.assertIsNone(data["action"])

    # 7. Enriched Valid Event Reaches Frozen Inference
    def test_07_enriched_valid_event_evaluates(self):
        notes = {
            "step": 452,
            "type": "TRANSFER",
            "oldbalanceOrg": 284100.50,
            "oldbalanceDest": 0.00,
            "nameOrig": "C_VICTIM_P0",
            "nameDest": "C_MULE_P0"
        }
        payload = self.make_sample_payload(
            payment_id="pay_enriched_drain_001",
            amount_paise=28410050,
            notes=notes
        )
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["evaluation_status"], "EVALUATED_ENRICHED_TEST_MODE")
        self.assertIsNotNone(data["risk_score"])
        self.assertGreaterEqual(data["risk_score"], 0.990)
        self.assertEqual(data["decision"], "DECLINED")
        self.assertEqual(data["action"], "DECLINE")
        self.assertEqual(data["engine_metadata"]["engine_version"], "v2.8.0-prod")
        self.assertIsNotNone(data["audit_id"])

    # 8. Incomplete Enriched Event Does Not Reach Inference
    def test_08_incomplete_enriched_event_rejected_safely(self):
        notes = {
            "oldbalanceOrg": 5000.00
        }
        payload = self.make_sample_payload(payment_id="pay_partial_notes_001", notes=notes)
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["evaluation_status"], "INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION")
        self.assertIsNone(data["risk_score"])

    # 9. Evaluation Creates Audit Record & Query Endpoint
    def test_09_webhook_event_logged_and_queried(self):
        payload = self.make_sample_payload(payment_id="pay_audit_query_001")
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})

        events_resp = self.client.get("/v1/webhooks/events?limit=10")
        self.assertEqual(events_resp.status_code, 200)
        events = events_resp.json()
        self.assertGreaterEqual(len(events), 1)
        self.assertTrue(any(e["payment_id"] == "pay_audit_query_001" for e in events))

    # 10. Model and Policy Versions Recorded When Evaluated
    def test_10_model_and_policy_versions_recorded(self):
        notes = {
            "step": 450,
            "type": "PAYMENT",
            "oldbalanceOrg": 1200.00,
            "oldbalanceDest": 0.00
        }
        payload = self.make_sample_payload(payment_id="pay_lineage_001", amount_paise=8450, notes=notes)
        raw_body = json.dumps(payload).encode("utf-8")
        sig = self.compute_signature(raw_body)

        resp = self.client.post("/v1/webhooks/razorpay", content=raw_body, headers={"X-Razorpay-Signature": sig})
        data = resp.json()
        self.assertEqual(data["evaluation_status"], "EVALUATED_ENRICHED_TEST_MODE")
        self.assertEqual(data["engine_metadata"]["model_version"], "model_b_stateful_hgb_v1.0.0")
        self.assertEqual(data["engine_metadata"]["policy_version"], "v1.2.0-frozen")
        self.assertEqual(data["engine_metadata"]["operating_threshold"], 0.990)

if __name__ == "__main__":
    unittest.main()
