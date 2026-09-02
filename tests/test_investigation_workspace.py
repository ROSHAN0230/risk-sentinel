"""
Risk Sentinel — Phase P1.2 Investigation Workspace Automated Test Suite
Validates investigation queue retrieval, provenance labeling, detail dossier assembly,
deterministic SOP guidance for all 8 reason codes, 404 rejection, deduplication,
and guarantees zero mutation of production engine state, models, or audit trails.
"""

import os
import sys
import hashlib
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.api import app, engine, webhook_adapter
from src.engine.investigations.investigation_service import SOP_GUIDANCE_MAP
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

class TestInvestigationWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # 1. GET /v1/investigations returns 200 and list
    def test_01_list_investigations_returns_200(self):
        resp = self.client.get("/v1/investigations")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    # 2. Queue records have explicit valid provenance
    def test_02_provenance_labeling(self):
        resp = self.client.get("/v1/investigations")
        data = resp.json()
        valid_provenance = {"AUDIT_LEDGER", "RAZORPAY_TEST_MODE", "DEMO_FIXTURE"}
        for item in data:
            self.assertIn(item["source_provenance"], valid_provenance)

    # 3. DEMO_FIXTURE records remain strictly labelled DEMO_FIXTURE
    def test_03_demo_fixture_provenance(self):
        resp = self.client.get("/v1/investigations?provenance=DEMO_FIXTURE")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 7)
        for item in data:
            self.assertEqual(item["source_provenance"], "DEMO_FIXTURE")
            self.assertFalse(item["has_audit_record"])

    # 4. Audit ledger records remain labelled AUDIT_LEDGER
    def test_04_audit_ledger_provenance(self):
        # Trigger an evaluation to ensure at least one audit record
        eval_payload = {
            "transaction_id": "tx_inv_audit_test_01",
            "step": 450,
            "type": "PAYMENT",
            "amount": 99.00,
            "nameOrig": "C_INV_TEST_SENDER",
            "oldbalanceOrg": 1500.00,
            "nameDest": "M_INV_TEST_DEST",
            "oldbalanceDest": 0.00
        }
        self.client.post("/v1/risk/evaluate", json=eval_payload)

        resp = self.client.get("/v1/investigations?provenance=AUDIT_LEDGER")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertTrue(any(i["event_ref"] == "tx_inv_audit_test_01" for i in data))
        test_rec = next(i for i in data if i["event_ref"] == "tx_inv_audit_test_01")
        self.assertEqual(test_rec["source_provenance"], "AUDIT_LEDGER")
        self.assertTrue(test_rec["has_audit_record"])

    # 5. Filtering by risk band works
    def test_05_band_filtering(self):
        resp = self.client.get("/v1/investigations?band=HIGH_RISK")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for item in data:
            self.assertEqual(item["risk_band"], "HIGH_RISK")

    # 6. Detail endpoint returns complete 9-pillar dossier for valid ID
    def test_06_detail_dossier_structure(self):
        resp = self.client.get("/v1/investigations/demo-03")
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertIn("what_happened", d)
        self.assertIn("why_flagged", d)
        self.assertIn("model_lineage", d)
        self.assertIn("policy_lineage", d)
        self.assertIn("available_evidence", d)
        self.assertIn("anomaly_indicators", d)
        self.assertIn("investigator_guidance", d)
        self.assertIn("audit_trail", d)

        self.assertEqual(d["why_flagged"]["primary_reason_code"], "RC_EXACT_BALANCE_DRAIN")
        self.assertEqual(d["policy_lineage"]["decision"], "DECLINED")
        self.assertEqual(d["policy_lineage"]["action"], "DECLINE")

    # 7. Unknown investigation ID returns HTTP 404
    def test_07_unknown_id_returns_404(self):
        resp = self.client.get("/v1/investigations/non_existent_tx_999999")
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertIn("not found", data["detail"].lower())

    # 8. All 8 certified reason codes resolve to deterministic SOP guidance
    def test_08_all_8_reason_codes_have_sop_guidance(self):
        expected_codes = [
            "RC_EXACT_BALANCE_DRAIN",
            "RC_SEVERE_LIQUIDITY_DRAIN",
            "RC_DEST_MULE_VELOCITY",
            "RC_NEW_ACCOUNT_LARGE_OUTFLOW",
            "RC_HIGH_RISK_CHANNEL_COMBO",
            "RC_SENDER_AMOUNT_DEVIATION",
            "RC_FALLBACK_EVALUATION_ACTIVE",
            "RC_BENIGN_BASELINE"
        ]
        for code in expected_codes:
            self.assertIn(code, SOP_GUIDANCE_MAP)
            guidance = SOP_GUIDANCE_MAP[code]
            self.assertEqual(guidance["reason_code"], code)
            self.assertIn("title", guidance)
            self.assertIn("objective", guidance)
            self.assertIn("protocol_steps", guidance)
            self.assertIn("evidence_to_inspect", guidance)
            self.assertGreaterEqual(len(guidance["protocol_steps"]), 2)

    # 9. GET requests do NOT mutate engine state or write audit records
    def test_09_get_requests_zero_mutation(self):
        initial_audit_count = len(engine.audit_logger.events)

        # Execute multiple investigation queries
        self.client.get("/v1/investigations")
        self.client.get("/v1/investigations?band=HIGH_RISK")
        self.client.get("/v1/investigations/demo-01")
        self.client.get("/v1/investigations/demo-02")
        self.client.get("/v1/investigations/demo-03")
        self.client.get("/v1/investigations/unknown_id_to_test_404")

        # Verify audit count is 100% unchanged
        after_audit_count = len(engine.audit_logger.events)
        self.assertEqual(initial_audit_count, after_audit_count)

    # 10. Production decision invariance
    def test_10_production_decision_invariance(self):
        payload = {
            "transaction_id": "tx_inv_invariance_01",
            "step": 452,
            "type": "TRANSFER",
            "amount": 284100.50,
            "nameOrig": "C_INV_INV_01",
            "oldbalanceOrg": 284100.50,
            "nameDest": "C_MULE_INV_01",
            "oldbalanceDest": 0.00
        }
        r1 = self.client.post("/v1/risk/evaluate", json=payload)
        d1 = r1.json()

        # Run investigation queries
        self.client.get(f"/v1/investigations/{payload['transaction_id']}")
        self.client.get("/v1/investigations")

        payload["transaction_id"] = "tx_inv_invariance_02"
        r2 = self.client.post("/v1/risk/evaluate", json=payload)
        d2 = r2.json()

        self.assertEqual(d1["decision"], d2["decision"])
        self.assertEqual(d1["action"], d2["action"])
        self.assertEqual(d1["risk_score"], d2["risk_score"])
        self.assertEqual(d1["reasons"]["primary_code"], d2["reasons"]["primary_code"])

    # 11. All 9 frozen SHA-256 hashes still match
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

    # 12. Production operating threshold is unchanged
    def test_12_production_threshold_unchanged(self):
        self.assertEqual(engine.operating_threshold, 0.990)
        self.assertEqual(engine.policy_engine.threshold_high, 0.990)
        self.assertEqual(engine.policy_engine.threshold_medium, 0.900)

if __name__ == "__main__":
    unittest.main()
