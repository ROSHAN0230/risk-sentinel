"""
Unit Tests: Audit Logger & Hash Chaining Integrity (tests/test_audit_logger.py)
"""

import unittest
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.audit_logger import mask_account_id

class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        self.engine = RiskDecisionEngine()
        self.engine.audit_logger.clear()

    def test_pii_masking_utility(self):
        self.assertEqual(mask_account_id("C123456789"), "C123***789")
        self.assertEqual(mask_account_id("M987654321"), "M987***321")
        self.assertEqual(mask_account_id("C12"), "C1***")

    def test_cryptographic_hash_chaining(self):
        req1 = EvaluateRequest(
            transaction_id="tx-aud-1",
            step=10,
            type=TransactionType.TRANSFER,
            amount=100.0,
            nameOrig="C111111",
            oldbalanceOrg=1000.0,
            nameDest="C222222",
            oldbalanceDest=0.0
        )
        req2 = EvaluateRequest(
            transaction_id="tx-aud-2",
            step=11,
            type=TransactionType.CASH_OUT,
            amount=200.0,
            nameOrig="C333333",
            oldbalanceOrg=2000.0,
            nameDest="C444444",
            oldbalanceDest=100.0
        )
        
        self.engine.evaluate(req1)
        self.engine.evaluate(req2)
        
        events = self.engine.audit_logger.get_events(limit=10)
        self.assertEqual(len(events), 2)
        
        hash1 = events[0]["integrity_hash"]
        hash2 = events[1]["integrity_hash"]
        
        self.assertTrue(len(hash1) == 64)
        self.assertTrue(len(hash2) == 64)
        self.assertNotEqual(hash1, hash2)
        
        # Verify PII masking in snapshot
        self.assertEqual(events[0]["input_snapshot_masked"]["sender_masked"], "C111***111")
        self.assertEqual(events[0]["input_snapshot_masked"]["dest_masked"], "C222***222")

if __name__ == "__main__":
    unittest.main()
