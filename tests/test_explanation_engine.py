"""
Unit Tests: Hybrid Causal Explanation Resolver (tests/test_explanation_engine.py)
"""

import unittest
from src.engine.schemas import EvaluateRequest, TransactionType, RiskBand
from src.engine.explanation_resolver import ExplanationResolver

class TestExplanationEngine(unittest.TestCase):
    def setUp(self):
        self.resolver = ExplanationResolver()

    def test_exact_balance_drain_explanation(self):
        req = EvaluateRequest(
            transaction_id="tx-exp-1",
            step=10,
            type=TransactionType.TRANSFER,
            amount=150000.0,
            nameOrig="C1",
            oldbalanceOrg=150000.0,
            nameDest="C2",
            oldbalanceDest=0.0
        )
        state_ctx = {"sender": None, "dest": None, "pair": None}
        reasons = self.resolver.resolve_explanations(req, score=0.998, band=RiskBand.HIGH_RISK, state_ctx=state_ctx)
        
        self.assertEqual(reasons.primary_code, "RC_EXACT_BALANCE_DRAIN")
        self.assertIn("RC_EXACT_BALANCE_DRAIN", reasons.all_codes)
        self.assertIn("100% liquidation", reasons.narrative)
        self.assertEqual(reasons.causal_evidence["liquidation_pct"], 100.0)

    def test_severe_liquidity_drain_explanation(self):
        req = EvaluateRequest(
            transaction_id="tx-exp-2",
            step=10,
            type=TransactionType.CASH_OUT,
            amount=95000.0,
            nameOrig="C1",
            oldbalanceOrg=100000.0,
            nameDest="C2",
            oldbalanceDest=500.0
        )
        state_ctx = {"sender": None, "dest": None, "pair": None}
        reasons = self.resolver.resolve_explanations(req, score=0.992, band=RiskBand.HIGH_RISK, state_ctx=state_ctx)
        
        self.assertEqual(reasons.primary_code, "RC_SEVERE_LIQUIDITY_DRAIN")
        self.assertIn("drains 95.0% of sender", reasons.narrative)

    def test_destination_mule_velocity_explanation(self):
        req = EvaluateRequest(
            transaction_id="tx-exp-3",
            step=10,
            type=TransactionType.TRANSFER,
            amount=10000.0,
            nameOrig="C1",
            oldbalanceOrg=50000.0,
            nameDest="C_MULE",
            oldbalanceDest=1000.0
        )
        # Mock destination with 5 incoming txs from 4 unique senders
        state_ctx = {
            "sender": None,
            "dest": [5, 50000.0, 20000.0, 9, {"S1", "S2", "S3", "S4"}],
            "pair": None
        }
        reasons = self.resolver.resolve_explanations(req, score=0.92, band=RiskBand.MEDIUM_RISK, state_ctx=state_ctx)
        self.assertIn("RC_DEST_MULE_VELOCITY", reasons.all_codes)

if __name__ == "__main__":
    unittest.main()
