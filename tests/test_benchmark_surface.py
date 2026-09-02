"""
Risk Sentinel — Phase 3 Benchmark & Evaluation Surface Test Suite
Verifies:
1. API contract: GET /v1/analytics/benchmark-summary returns 200 with complete schema.
2. Canonical benchmark figures: 955,744 transactions, 4,010 frauds, 3,996 TP, 154 FP, 14 FN, 951,580 TN.
3. Confusion matrix arithmetic exactness: TP + FP + FN + TN == 955,744.
4. Precision and recall precision: 96.29% precision, 99.65% recall.
5. Financial outcomes: $6,323,408,725.18 intercepted, $399,045.08 missed, 99.9937% capture rate.
6. Operating threshold provenance: 0.990 locked, 0.900 secondary.
7. Read-only behavior: Zero mutation of state_store or audit_logger.
8. Frozen artifact integrity: All 9 core files match baseline SHA-256 hashes.
"""

import unittest
import hashlib
from fastapi.testclient import TestClient

from src.engine.api import app, engine as prod_engine
from src.engine.analytics.economics_service import EconomicsService

class TestBenchmarkSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.economics = EconomicsService()

    def test_01_benchmark_summary_endpoint_contract(self):
        """GET /v1/analytics/benchmark-summary returns 200 with full schema."""
        resp = self.client.get("/v1/analytics/benchmark-summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        expected_keys = [
            "dataset_name", "dataset_file", "evaluation_split", "total_transactions",
            "fraud_transactions", "operating_threshold", "secondary_threshold",
            "confusion_matrix", "precision_percent", "recall_percent",
            "fraud_dollars_intercepted", "fraud_dollars_missed",
            "fraud_dollar_interception_percent", "flagged_nonfraud_volume",
            "disclaimer", "threshold_provenance_note"
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Missing key in benchmark summary: {key}")

    def test_02_canonical_held_out_transaction_counts(self):
        """Verifies exact canonical held-out test counts."""
        data = self.economics.get_benchmark_summary()
        self.assertEqual(data["total_transactions"], 955744)
        self.assertEqual(data["fraud_transactions"], 4010)

    def test_03_confusion_matrix_arithmetic_and_balance(self):
        """Verifies exact 4-cell confusion matrix numbers and arithmetic balance."""
        data = self.economics.get_benchmark_summary()
        cm = data["confusion_matrix"]

        self.assertEqual(cm["tp"], 3996)
        self.assertEqual(cm["fp"], 154)
        self.assertEqual(cm["fn"], 14)
        self.assertEqual(cm["tn"], 951580)

        # Exact arithmetic balance
        self.assertEqual(cm["tp"] + cm["fp"] + cm["fn"] + cm["tn"], 955744)
        self.assertEqual(cm["tp"] + cm["fn"], 4010)
        self.assertEqual(cm["fp"] + cm["tn"], 951734)

    def test_04_precision_and_recall_calculation(self):
        """Verifies 96.29% precision and 99.65% recall."""
        data = self.economics.get_benchmark_summary()
        self.assertAlmostEqual(data["precision_percent"], 96.29, places=2)
        self.assertAlmostEqual(data["recall_percent"], 99.65, places=2)

    def test_05_financial_outcomes_and_dollar_interception(self):
        """Verifies $6.323B intercepted, $399k missed, and 99.9937% capture rate."""
        data = self.economics.get_benchmark_summary()
        self.assertEqual(data["fraud_dollars_intercepted"], 6323408725.18)
        self.assertEqual(data["fraud_dollars_missed"], 399045.08)
        self.assertAlmostEqual(data["fraud_dollar_interception_percent"], 99.9937, places=4)
        self.assertEqual(data["flagged_nonfraud_volume"], 9216222.88)

    def test_06_operating_threshold_provenance(self):
        """Operating threshold is locked at 0.990; secondary is 0.900."""
        data = self.economics.get_benchmark_summary()
        self.assertEqual(data["operating_threshold"], 0.990)
        self.assertEqual(data["secondary_threshold"], 0.900)
        self.assertIn("validation steps 323", data["threshold_provenance_note"])

    def test_07_read_only_zero_mutation(self):
        """Calling the benchmark summary endpoint 25 times produces zero mutation in state or audit logs."""
        initial_audit_len = len(prod_engine.audit_logger.events)
        initial_sender_keys = set(prod_engine.state_store.sender_state.keys())
        initial_dest_keys = set(prod_engine.state_store.dest_state.keys())

        for _ in range(25):
            resp = self.client.get("/v1/analytics/benchmark-summary")
            self.assertEqual(resp.status_code, 200)

        self.assertEqual(len(prod_engine.audit_logger.events), initial_audit_len)
        self.assertEqual(set(prod_engine.state_store.sender_state.keys()), initial_sender_keys)
        self.assertEqual(set(prod_engine.state_store.dest_state.keys()), initial_dest_keys)

    def test_08_disclaimer_presence(self):
        """Ensures the synthetic PaySim benchmark disclaimer is permanently present."""
        data = self.economics.get_benchmark_summary()
        self.assertIn("PaySim synthetic benchmark", data["disclaimer"])
        self.assertIn("Not Razorpay production performance", data["disclaimer"])

    def test_09_all_9_frozen_hashes_match(self):
        """Verifies byte-for-byte SHA-256 match for all 9 frozen core files."""
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

if __name__ == '__main__':
    unittest.main()
