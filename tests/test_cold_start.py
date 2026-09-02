"""
Unit Tests: Non-Prejudicial Cold-Start Contextual Evaluation (tests/test_cold_start.py)
"""

import unittest
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.state_store import InMemoryStateStore

class TestColdStart(unittest.TestCase):
    def setUp(self):
        self.state_store = InMemoryStateStore()
        self.engine = RiskDecisionEngine(state_store=self.state_store)

    def test_benign_cold_start_approved_seamlessly(self):
        """
        Verify that a brand new account (unseen sender, unseen destination)
        performing a normal, non-draining transfer is APPROVED without penalty.
        """
        req = EvaluateRequest(
            transaction_id="tx-cold-benign",
            step=150,
            type=TransactionType.TRANSFER,
            amount=50.0,
            nameOrig="NEW_USER_9999",
            oldbalanceOrg=1000.0,  # 5% transfer, not a full drain
            nameDest="NEW_MERCHANT_8888",
            oldbalanceDest=500.0
        )
        
        resp = self.engine.evaluate(req)
        self.assertEqual(resp.risk_band.value, "LOW_RISK")
        self.assertEqual(resp.decision.value, "APPROVED")
        self.assertEqual(resp.action.value, "APPROVE")
        
        # Verify cold start context logged
        events = self.engine.audit_logger.get_events(limit=1)
        self.assertEqual(events[0]["causal_features_extracted"]["is_sender_cold_start"], 1.0)
        self.assertEqual(events[0]["causal_features_extracted"]["is_dest_cold_start"], 1.0)

    def test_malicious_cold_start_drain_isolated(self):
        """
        Verify that a brand new account attempting an immediate 100% balance drain
        is flagged based on point-in-time liquidity physics, not because it is cold start.
        """
        req = EvaluateRequest(
            transaction_id="tx-cold-drain",
            step=150,
            type=TransactionType.TRANSFER,
            amount=50000.0,
            nameOrig="FRAUD_USER_0001",
            oldbalanceOrg=50000.0,  # 100% drain
            nameDest="MULE_0001",
            oldbalanceDest=0.0
        )
        
        resp = self.engine.evaluate(req)
        self.assertEqual(resp.risk_band.value, "HIGH_RISK")
        self.assertEqual(resp.decision.value, "DECLINED")
        self.assertEqual(resp.action.value, "DECLINE")
        self.assertEqual(resp.reasons.primary_code, "RC_EXACT_BALANCE_DRAIN")

if __name__ == "__main__":
    unittest.main()
