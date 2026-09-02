"""
Unit Tests: Phase 2.8 Failure & Edge-Case Matrix (tests/test_failure_matrix.py)
"""

import unittest
from pydantic import ValidationError
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.state_store import InMemoryStateStore

class TestFailureMatrix(unittest.TestCase):
    def setUp(self):
        self.engine = RiskDecisionEngine()

    def test_case_1_and_2_missing_or_malformed_fields(self):
        with self.assertRaises(ValidationError):
            EvaluateRequest(
                transaction_id="tx-bad",
                step=1,
                type=TransactionType.TRANSFER
                # Missing amount, nameOrig, nameDest
            )

    def test_case_3_negative_amount(self):
        with self.assertRaises(ValidationError):
            EvaluateRequest(
                transaction_id="tx-neg",
                step=1,
                type=TransactionType.TRANSFER,
                amount=-100.0,
                nameOrig="C1",
                oldbalanceOrg=100.0,
                nameDest="C2",
                oldbalanceDest=0.0
            )

    def test_case_4_zero_amount(self):
        with self.assertRaises(ValidationError):
            EvaluateRequest(
                transaction_id="tx-zero",
                step=1,
                type=TransactionType.TRANSFER,
                amount=0.0,
                nameOrig="C1",
                oldbalanceOrg=100.0,
                nameDest="C2",
                oldbalanceDest=0.0
            )

    def test_case_5_unknown_channel_type(self):
        with self.assertRaises(ValidationError):
            EvaluateRequest(
                transaction_id="tx-unknown",
                step=1,
                type="BITCOIN_PAYMENT", # Invalid
                amount=100.0,
                nameOrig="C1",
                oldbalanceOrg=100.0,
                nameDest="C2",
                oldbalanceDest=0.0
            )

    def test_case_8_state_store_unreachable_fallback(self):
        broken_store = InMemoryStateStore(force_failure=True)
        engine_fallback = RiskDecisionEngine(state_store=broken_store)
        req = EvaluateRequest(
            transaction_id="tx-broken-store",
            step=10,
            type=TransactionType.TRANSFER,
            amount=500.0,
            nameOrig="C1",
            oldbalanceOrg=1000.0,
            nameDest="C2",
            oldbalanceDest=0.0
        )
        resp = engine_fallback.evaluate(req)
        self.assertTrue(resp.engine_metadata.fallback_triggered)
        self.assertEqual(resp.engine_metadata.model_type, "MODEL_A_CAUSAL_BASELINE_FALLBACK")

    def test_case_13_extreme_astronomical_amount(self):
        req = EvaluateRequest(
            transaction_id="tx-extreme",
            step=10,
            type=TransactionType.TRANSFER,
            amount=999999999.0, # $1B transfer
            nameOrig="C_WHALE",
            oldbalanceOrg=999999999.0,
            nameDest="C_DEST",
            oldbalanceDest=0.0
        )
        resp = self.engine.evaluate(req)
        self.assertEqual(resp.risk_band.value, "HIGH_RISK")
        self.assertEqual(resp.decision.value, "DECLINED")

if __name__ == "__main__":
    unittest.main()
