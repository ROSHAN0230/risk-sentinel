"""
Integration Tests: FastAPI Service Endpoints (tests/test_api_integration.py)
"""

import unittest
from fastapi.testclient import TestClient
from src.engine.api import app

class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertTrue(data["state_store_responsive"])

    def test_model_info_endpoint(self):
        response = self.client.get("/v1/model/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("model_a", data)
        self.assertIn("model_b", data)
        self.assertEqual(data["engine_version"], "v2.8.0-prod")

    def test_evaluate_endpoint_approved(self):
        payload = {
            "transaction_id": "api-tx-001",
            "step": 200,
            "type": "PAYMENT",
            "amount": 45.0,
            "nameOrig": "C_BUYER_1",
            "oldbalanceOrg": 500.0,
            "nameDest": "M_MERCHANT_1",
            "oldbalanceDest": 0.0
        }
        response = self.client.post("/v1/risk/evaluate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["decision"], "APPROVED")
        self.assertEqual(data["action"], "APPROVE")
        self.assertEqual(data["risk_band"], "LOW_RISK")

    def test_evaluate_endpoint_declined(self):
        payload = {
            "transaction_id": "api-tx-002",
            "step": 201,
            "type": "TRANSFER",
            "amount": 250000.0,
            "nameOrig": "C_VICTIM_2",
            "oldbalanceOrg": 250000.0,
            "nameDest": "C_MULE_2",
            "oldbalanceDest": 0.0
        }
        response = self.client.post("/v1/risk/evaluate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["decision"], "DECLINED")
        self.assertEqual(data["action"], "DECLINE")
        self.assertEqual(data["risk_band"], "HIGH_RISK")
        self.assertEqual(data["reasons"]["primary_code"], "RC_EXACT_BALANCE_DRAIN")

    def test_evaluate_endpoint_schema_error(self):
        payload = {
            "transaction_id": "api-tx-003",
            "step": 202,
            "type": "TRANSFER",
            "amount": -50.0 # Invalid negative amount
        }
        response = self.client.post("/v1/risk/evaluate", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_audit_events_endpoint(self):
        # Post a transaction first to guarantee at least one audit event
        payload = {
            "transaction_id": "api-tx-aud-test",
            "step": 200,
            "type": "PAYMENT",
            "amount": 10.0,
            "nameOrig": "C_AUD_1",
            "oldbalanceOrg": 100.0,
            "nameDest": "M_AUD_1",
            "oldbalanceDest": 0.0
        }
        self.client.post("/v1/risk/evaluate", json=payload)
        
        response = self.client.get("/v1/audit/events?limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) >= 1)

if __name__ == "__main__":
    unittest.main()
