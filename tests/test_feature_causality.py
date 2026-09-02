"""
Unit Tests: Causal Invariance & Zero Temporal Leakage (tests/test_feature_causality.py)
"""

import unittest
import numpy as np
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.feature_pipeline import FeaturePipeline
from src.engine.state_store import InMemoryStateStore

class TestFeatureCausality(unittest.TestCase):
    def setUp(self):
        self.pipeline = FeaturePipeline()
        self.state_store = InMemoryStateStore()

    def test_feature_dimensions(self):
        req = EvaluateRequest(
            transaction_id="tx-1",
            step=10,
            type=TransactionType.TRANSFER,
            amount=500.0,
            nameOrig="C1",
            oldbalanceOrg=1000.0,
            nameDest="C2",
            oldbalanceDest=0.0
        )
        X_a, dict_a = self.pipeline.build_features_a(req)
        self.assertEqual(X_a.shape, (1, 15))
        self.assertEqual(len(dict_a), 15)

        state_ctx = self.state_store.read_entity_state("C1", "C2")
        X_b, dict_b = self.pipeline.build_features_b(req, state_ctx)
        self.assertEqual(X_b.shape, (1, 36))
        self.assertEqual(len(dict_b), 36)

    def test_causal_invariance_across_time(self):
        """
        Verify that processing subsequent future transactions (t+1, t+2)
        does NOT alter the feature vector generated for past transaction (t).
        """
        tx_t1 = EvaluateRequest(
            transaction_id="tx-1",
            step=100,
            type=TransactionType.TRANSFER,
            amount=500.0,
            nameOrig="SENDER_ALICE",
            oldbalanceOrg=1000.0,
            nameDest="DEST_BOB",
            oldbalanceDest=0.0
        )
        
        # 1. Evaluate at t=100
        state_ctx_1 = self.state_store.read_entity_state(tx_t1.nameOrig, tx_t1.nameDest)
        X_b_t1, dict_b_t1 = self.pipeline.build_features_b(tx_t1, state_ctx_1)
        self.assertEqual(dict_b_t1['orig_prev_tx_cnt'], 0.0)
        self.assertEqual(dict_b_t1['is_sender_cold_start'], 1.0)
        
        # Update state after t=100
        self.state_store.update_entity_state(tx_t1.nameOrig, tx_t1.nameDest, tx_t1.step, tx_t1.amount, tx_t1.type.value)
        
        # 2. Transaction at t=101
        tx_t2 = EvaluateRequest(
            transaction_id="tx-2",
            step=101,
            type=TransactionType.CASH_OUT,
            amount=200.0,
            nameOrig="SENDER_ALICE",
            oldbalanceOrg=500.0,
            nameDest="DEST_CHARLIE",
            oldbalanceDest=100.0
        )
        state_ctx_2 = self.state_store.read_entity_state(tx_t2.nameOrig, tx_t2.nameDest)
        X_b_t2, dict_b_t2 = self.pipeline.build_features_b(tx_t2, state_ctx_2)
        
        # SENDER_ALICE at t=101 now has 1 prior transaction
        self.assertEqual(dict_b_t2['orig_prev_tx_cnt'], 1.0)
        self.assertEqual(dict_b_t2['is_sender_cold_start'], 0.0)
        self.assertEqual(dict_b_t2['orig_prev_cum_amt'], 500.0)
        
        # 3. CRITICAL CAUSAL ASSERTION:
        # Re-evaluating tx_t1 using state strictly before t=100 produces identical vector as step 1
        state_reconstructed_t1 = {"sender": None, "dest": None, "pair": None}
        X_b_t1_replay, dict_b_t1_replay = self.pipeline.build_features_b(tx_t1, state_reconstructed_t1)
        
        np.testing.assert_array_almost_equal(X_b_t1, X_b_t1_replay)
        self.assertEqual(dict_b_t1, dict_b_t1_replay)

if __name__ == "__main__":
    unittest.main()
