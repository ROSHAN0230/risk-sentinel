"""
Unit Tests: Sequential State Read-Before / Write-After Lifecycle (tests/test_state_lifecycle.py)
"""

import unittest
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.state_store import InMemoryStateStore

class TestStateLifecycle(unittest.TestCase):
    def setUp(self):
        self.state_store = InMemoryStateStore()
        self.engine = RiskDecisionEngine(state_store=self.state_store)

    def test_read_before_write_ordering(self):
        req1 = EvaluateRequest(
            transaction_id="tx-lifecycle-1",
            step=50,
            type=TransactionType.TRANSFER,
            amount=1000.0,
            nameOrig="USER_X",
            oldbalanceOrg=2000.0,
            nameDest="MERCHANT_Y",
            oldbalanceDest=0.0
        )
        
        # On first transaction, state must be cold-start (0 past transactions)
        resp1 = self.engine.evaluate(req1)
        self.assertFalse(resp1.engine_metadata.fallback_triggered)
        
        # Check audit log features for tx1
        events = self.engine.audit_logger.get_events(limit=1)
        self.assertEqual(events[0]["causal_features_extracted"]["orig_prev_tx_cnt"], 0.0)
        self.assertEqual(events[0]["causal_features_extracted"]["is_sender_cold_start"], 1.0)
        
        # After evaluate finishes, state store now has 1 transaction
        state_after_1 = self.state_store.read_entity_state("USER_X", "MERCHANT_Y")
        self.assertEqual(state_after_1["sender"][0], 1)
        self.assertEqual(state_after_1["sender"][1], 1000.0)
        
        # Second transaction from USER_X
        req2 = EvaluateRequest(
            transaction_id="tx-lifecycle-2",
            step=51,
            type=TransactionType.TRANSFER,
            amount=500.0,
            nameOrig="USER_X",
            oldbalanceOrg=1000.0,
            nameDest="MERCHANT_Z",
            oldbalanceDest=100.0
        )
        resp2 = self.engine.evaluate(req2)
        events2 = self.engine.audit_logger.get_events(limit=2)
        
        # Features for tx2 must observe exactly 1 prior transaction
        self.assertEqual(events2[1]["causal_features_extracted"]["orig_prev_tx_cnt"], 1.0)
        self.assertEqual(events2[1]["causal_features_extracted"]["is_sender_cold_start"], 0.0)
        self.assertEqual(events2[1]["causal_features_extracted"]["orig_prev_cum_amt"], 1000.0)

if __name__ == "__main__":
    unittest.main()
