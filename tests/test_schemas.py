"""
Unit Tests: Input Schemas & Request/Response Validation (tests/test_schemas.py)
"""

import unittest
from pydantic import ValidationError
from src.engine.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    TransactionType,
    RiskBand,
    DecisionEnum,
    ActionEnum
)

class TestSchemas(unittest.TestCase):
    def test_valid_request(self):
        payload = {
            "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
            "step": 350,
            "type": "TRANSFER",
            "amount": 1000.50,
            "nameOrig": "C12345",
            "oldbalanceOrg": 5000.0,
            "nameDest": "C67890",
            "oldbalanceDest": 200.0
        }
        req = EvaluateRequest(**payload)
        self.assertEqual(req.transaction_id, "550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(req.type, TransactionType.TRANSFER)
        self.assertEqual(req.amount, 1000.50)

    def test_negative_amount_rejection(self):
        payload = {
            "transaction_id": "tx-1",
            "step": 1,
            "type": "TRANSFER",
            "amount": -50.0,
            "nameOrig": "C1",
            "oldbalanceOrg": 100.0,
            "nameDest": "C2",
            "oldbalanceDest": 0.0
        }
        with self.assertRaises(ValidationError):
            EvaluateRequest(**payload)

    def test_zero_amount_rejection(self):
        payload = {
            "transaction_id": "tx-1",
            "step": 1,
            "type": "TRANSFER",
            "amount": 0.0,
            "nameOrig": "C1",
            "oldbalanceOrg": 100.0,
            "nameDest": "C2",
            "oldbalanceDest": 0.0
        }
        with self.assertRaises(ValidationError):
            EvaluateRequest(**payload)

    def test_negative_balance_rejection(self):
        payload = {
            "transaction_id": "tx-1",
            "step": 1,
            "type": "TRANSFER",
            "amount": 100.0,
            "nameOrig": "C1",
            "oldbalanceOrg": -10.0,
            "nameDest": "C2",
            "oldbalanceDest": 0.0
        }
        with self.assertRaises(ValidationError):
            EvaluateRequest(**payload)

    def test_unknown_channel_type(self):
        payload = {
            "transaction_id": "tx-1",
            "step": 1,
            "type": "CRYPTO_SWAP",
            "amount": 100.0,
            "nameOrig": "C1",
            "oldbalanceOrg": 100.0,
            "nameDest": "C2",
            "oldbalanceDest": 0.0
        }
        with self.assertRaises(ValidationError):
            EvaluateRequest(**payload)

    def test_missing_mandatory_field(self):
        payload = {
            "transaction_id": "tx-1",
            "step": 1,
            "type": "TRANSFER"
            # Missing amount and account IDs
        }
        with self.assertRaises(ValidationError):
            EvaluateRequest(**payload)

if __name__ == "__main__":
    unittest.main()
