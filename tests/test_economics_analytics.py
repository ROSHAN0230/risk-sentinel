"""
Risk Sentinel — Phase P1.1 Decision Economics & Cost Simulator Test Suite
Validates artifact loading, 15-point threshold ladder, alpha bounds, exact cost math,
validation vs test data separation, and guarantees zero mutation of production engine state.
"""

import os
import sys
import hashlib
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.api import app
from src.engine.analytics.economics_service import EconomicsService, VALIDATION_THRESHOLDS
from src.engine.schemas import EvaluateRequest, TransactionType

EXPECTED_FROZEN_HASHES = {
    "model_b_stateful_hgb.joblib": ("src/engine/artifacts/model_b_stateful_hgb.joblib", "5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735"),
    "model_a_causal_hgb.joblib": ("src/engine/artifacts/model_a_causal_hgb.joblib", "ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373"),
    "policy_engine.py": ("src/engine/policy_engine.py", "b61ab343af0e5aa84726db1d96700b89b8e22b88a597f73c97b8320b430b9b5e"),
    "decision_engine.py": ("src/engine/decision_engine.py", "1b5f1615f90548fa5eba94231e207d43d3e0bf7a6d68d47b802a56daaa747a4f"),
    "feature_pipeline.py": ("src/engine/feature_pipeline.py", "41b315ed0eaff96321d7dfabab72f5fdd1a254a39604445500d545bc55a7b993"),
    "model_manager.py": ("src/engine/model_manager.py", "e2400085415e93554e480d8ff4f78fe22852c007fc5926fc27da0352d5f6899a"),
    "schemas.py": ("src/engine/schemas.py", "de16b6bba9d2b235611adf52272ff033cb40eafff6ce92c2b7de56725ff093bf"),
    "audit_logger.py": ("src/engine/audit_logger.py", "044951b6a014a07cd48179cd9d5388373ddd2b4e0dc980934db1d980e4a68afb"),
    "state_store.py": ("src/engine/state_store.py", "f7f6615a0277bb11631fe4dbc0be5ddde26a1c28889eff6827243946b2b70d35")
}

class TestEconomicsAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.service = EconomicsService()

    # 1. Phase 2.7 artifacts load correctly
    def test_01_artifacts_load_cleanly(self):
        records = self.service.get_threshold_sensitivity()
        self.assertIsInstance(records, list)
        self.assertEqual(len(records), 15)

    # 2. Exact 15 threshold records are present
    def test_02_exact_15_threshold_records(self):
        records = self.service.get_threshold_sensitivity()
        thresholds = [r["threshold"] for r in records]
        self.assertEqual(thresholds, VALIDATION_THRESHOLDS)
        self.assertIn(0.990, thresholds)

    # 3. Alpha 0.001 is accepted (minimum boundary)
    def test_03_alpha_min_accepted(self):
        res = self.service.simulate_cost(alpha=0.001)
        self.assertEqual(res["alpha"], 0.001)
        self.assertEqual(res["alpha_percentage"], "0.1%")
        self.assertEqual(len(res["simulation_table"]), 15)

    # 4. Alpha 0.05 is accepted (maximum boundary)
    def test_04_alpha_max_accepted(self):
        res = self.service.simulate_cost(alpha=0.05)
        self.assertEqual(res["alpha"], 0.05)
        self.assertEqual(res["alpha_percentage"], "5.0%")

    # 5. Alpha below 0.001 is rejected
    def test_05_alpha_below_min_rejected(self):
        with self.assertRaises(ValueError):
            self.service.simulate_cost(alpha=0.0005)
        
        # Via API
        resp = self.client.get("/v1/analytics/cost-simulation?alpha=0.0005")
        self.assertEqual(resp.status_code, 400)

    # 6. Alpha above 0.05 is rejected
    def test_06_alpha_above_max_rejected(self):
        with self.assertRaises(ValueError):
            self.service.simulate_cost(alpha=0.06)

        # Via API
        resp = self.client.get("/v1/analytics/cost-simulation?alpha=0.06")
        self.assertEqual(resp.status_code, 400)

    # 7. Cost equation is exact: total_cost = missed_fraud_amount + alpha * flagged_nonfraud_amount
    def test_07_cost_equation_exactness(self):
        alpha = 0.015
        res = self.service.simulate_cost(alpha=alpha)
        for pt in res["simulation_table"]:
            expected_friction = round(alpha * pt["flagged_nonfraud_amount"], 4)
            expected_total = round(pt["missed_fraud_amount"] + expected_friction, 4)
            self.assertAlmostEqual(pt["friction_cost"], expected_friction, places=3)
            self.assertAlmostEqual(pt["total_cost"], expected_total, places=3)

    # 8. Validation metrics are not replaced with future-test metrics
    def test_08_validation_data_boundary(self):
        records = self.service.get_threshold_sensitivity()
        pt_990 = next(r for r in records if r["threshold"] == 0.990)
        # On Validation data: tp = 570, fn = 0, fp = 119
        self.assertEqual(pt_990["tp"], 570)
        self.assertEqual(pt_990["fn"], 0)
        self.assertEqual(pt_990["fp"], 119)
        self.assertEqual(pt_990["split"], "VALIDATION_SPLIT_STEPS_336_377")

    # 9. Frozen production threshold remains 0.990
    def test_09_production_threshold_marked(self):
        records = self.service.get_threshold_sensitivity()
        prod_records = [r for r in records if r["is_production_threshold"]]
        self.assertEqual(len(prod_records), 1)
        self.assertEqual(prod_records[0]["threshold"], 0.990)

    # 10. Production decision output is identical before/after analytics calls
    def test_10_production_inference_invariance(self):
        test_payload = {
            "transaction_id": "tx_econ_invariance_01",
            "step": 452,
            "type": "TRANSFER",
            "amount": 284100.50,
            "nameOrig": "C_INVARIANCE_01",
            "oldbalanceOrg": 284100.50,
            "nameDest": "C_MULE_01",
            "oldbalanceDest": 0.00
        }
        # First call before analytics
        resp_before = self.client.post("/v1/risk/evaluate", json=test_payload)
        self.assertEqual(resp_before.status_code, 200)
        data_before = resp_before.json()

        # Call analytics endpoints multiple times
        self.client.get("/v1/analytics/threshold-sensitivity")
        self.client.get("/v1/analytics/cost-simulation?alpha=0.01")
        self.client.get("/v1/analytics/cost-simulation?alpha=0.05")

        # Second call after analytics
        test_payload["transaction_id"] = "tx_econ_invariance_02"
        resp_after = self.client.post("/v1/risk/evaluate", json=test_payload)
        self.assertEqual(resp_after.status_code, 200)
        data_after = resp_after.json()

        # Assert identical decision semantics
        self.assertEqual(data_before["decision"], data_after["decision"])
        self.assertEqual(data_before["action"], data_after["action"])
        self.assertEqual(data_before["risk_score"], data_after["risk_score"])
        self.assertEqual(data_before["reasons"]["primary_code"], data_after["reasons"]["primary_code"])

    # 11 & 12. All 9 frozen SHA-256 hashes still match
    def test_11_all_9_frozen_hashes_match(self):
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name, (rel_path, exp_hash) in EXPECTED_FROZEN_HASHES.items():
            full_path = os.path.join(proj_root, rel_path.replace("/", os.sep))
            with open(full_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(
                actual_hash, exp_hash,
                f"Frozen hash violation in {name}: expected {exp_hash}, got {actual_hash}"
            )

    # 13. API smoke tests for both endpoints
    def test_12_api_smoke_test(self):
        r1 = self.client.get("/v1/analytics/threshold-sensitivity")
        self.assertEqual(r1.status_code, 200)
        data1 = r1.json()
        self.assertEqual(len(data1), 15)

        r2 = self.client.get("/v1/analytics/cost-simulation?alpha=0.02")
        self.assertEqual(r2.status_code, 200)
        data2 = r2.json()
        self.assertEqual(data2["alpha_percentage"], "2.0%")
        self.assertIn("production_operating_point", data2)
        self.assertEqual(data2["production_operating_point"]["threshold"], 0.990)

if __name__ == "__main__":
    unittest.main()
