"""
Unit Tests: Multithreaded State Consistency & Concurrency (tests/test_concurrency.py)
"""

import unittest
import threading
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine

class TestConcurrency(unittest.TestCase):
    def test_concurrent_transactions_state_consistency(self):
        engine = RiskDecisionEngine()
        num_threads = 20
        txs_per_thread = 25
        
        errors = []
        
        def worker(thread_idx: int):
            try:
                for i in range(txs_per_thread):
                    req = EvaluateRequest(
                        transaction_id=f"tx-t{thread_idx}-i{i}",
                        step=100 + i,
                        type=TransactionType.TRANSFER,
                        amount=10.0 + i,
                        nameOrig=f"USER_THREAD_{thread_idx}",
                        oldbalanceOrg=1000.0,
                        nameDest=f"MERCHANT_THREAD_{thread_idx}",
                        oldbalanceDest=100.0
                    )
                    resp = engine.evaluate(req)
                    if resp.decision is None:
                        errors.append(f"Null decision in thread {thread_idx}")
            except Exception as e:
                errors.append(f"Exception in thread {thread_idx}: {str(e)}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        self.assertEqual(len(errors), 0, f"Concurrency errors encountered: {errors}")
        
        # Verify each user has exactly txs_per_thread recorded in state store
        for t in range(num_threads):
            state = engine.state_store.read_entity_state(f"USER_THREAD_{t}", f"MERCHANT_THREAD_{t}")
            self.assertEqual(state["sender"][0], txs_per_thread)

if __name__ == "__main__":
    unittest.main()
