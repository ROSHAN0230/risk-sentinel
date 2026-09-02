"""
Unit Tests: Circuit Breaker & Graceful Model A Fallback (tests/test_fallback_circuit_breaker.py)
"""

import unittest
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.state_store import InMemoryStateStore

class TestFallbackCircuitBreaker(unittest.TestCase):
    def test_state_failure_triggers_model_a_fallback(self):
        # Create store with forced failure
        broken_store = InMemoryStateStore(force_failure=True)
        engine = RiskDecisionEngine(state_store=broken_store, state_timeout_ms=15.0)
        
        req = EvaluateRequest(
            transaction_id="tx-fallback-1",
            step=100,
            type=TransactionType.TRANSFER,
            amount=50000.0,
            nameOrig="SENDER_FALLBACK",
            oldbalanceOrg=50000.0,
            nameDest="DEST_FALLBACK",
            oldbalanceDest=0.0
        )
        
        resp = engine.evaluate(req)
        # Transaction must NOT fail
        self.assertTrue(resp.engine_metadata.fallback_triggered)
        self.assertEqual(resp.engine_metadata.model_type, "MODEL_A_CAUSAL_BASELINE_FALLBACK")
        self.assertIn("RC_FALLBACK_EVALUATION_ACTIVE", resp.reasons.all_codes)
        # For exact balance drain, Model A should still flag as HIGH_RISK -> DECLINE
        self.assertEqual(resp.decision.value, "DECLINED")

    def test_state_timeout_triggers_circuit_breaker(self):
        # Create store with 25ms artificial delay (exceeds 15ms SLA threshold)
        slow_store = InMemoryStateStore(simulate_latency_ms=25.0)
        engine = RiskDecisionEngine(state_store=slow_store, state_timeout_ms=15.0)
        
        req = EvaluateRequest(
            transaction_id="tx-fallback-2",
            step=100,
            type=TransactionType.TRANSFER,
            amount=1000.0,
            nameOrig="SENDER_SLOW",
            oldbalanceOrg=5000.0,
            nameDest="DEST_SLOW",
            oldbalanceDest=100.0
        )
        
        resp = engine.evaluate(req)
        self.assertTrue(resp.engine_metadata.fallback_triggered)
        self.assertEqual(resp.engine_metadata.model_type, "MODEL_A_CAUSAL_BASELINE_FALLBACK")

if __name__ == "__main__":
    unittest.main()
