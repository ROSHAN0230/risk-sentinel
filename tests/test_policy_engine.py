"""
Unit Tests: Decoupled Policy Resolution Engine (tests/test_policy_engine.py)
"""

import unittest
from src.engine.schemas import (
    EvaluateRequest,
    TransactionType,
    RiskBand,
    DecisionEnum,
    ActionEnum
)
from src.engine.policy_engine import PolicyEngine

class TestPolicyEngine(unittest.TestCase):
    def setUp(self):
        self.policy = PolicyEngine(threshold_high=0.990, threshold_medium=0.900)

    def test_risk_band_resolution(self):
        self.assertEqual(self.policy.resolve_risk_band(0.995), RiskBand.HIGH_RISK)
        self.assertEqual(self.policy.resolve_risk_band(0.990), RiskBand.HIGH_RISK)
        self.assertEqual(self.policy.resolve_risk_band(0.950), RiskBand.MEDIUM_RISK)
        self.assertEqual(self.policy.resolve_risk_band(0.900), RiskBand.MEDIUM_RISK)
        self.assertEqual(self.policy.resolve_risk_band(0.899), RiskBand.LOW_RISK)
        self.assertEqual(self.policy.resolve_risk_band(0.001), RiskBand.LOW_RISK)

    def test_fast_track_channel_bypass(self):
        for ch in [TransactionType.PAYMENT, TransactionType.CASH_IN, TransactionType.DEBIT]:
            req = EvaluateRequest(
                transaction_id="tx-bypass",
                step=1,
                type=ch,
                amount=1000.0,
                nameOrig="C1",
                oldbalanceOrg=2000.0,
                nameDest="C2",
                oldbalanceDest=0.0
            )
            dec, act = self.policy.resolve_decision_and_action(req, RiskBand.HIGH_RISK, score=0.995)
            self.assertEqual(dec, DecisionEnum.APPROVED)
            self.assertEqual(act, ActionEnum.APPROVE)

    def test_scored_channels_actions(self):
        req_tf = EvaluateRequest(
            transaction_id="tx-tf",
            step=1,
            type=TransactionType.TRANSFER,
            amount=10000.0,
            nameOrig="C1",
            oldbalanceOrg=20000.0,
            nameDest="C2",
            oldbalanceDest=0.0
        )
        
        # Low risk -> Approve
        dec, act = self.policy.resolve_decision_and_action(req_tf, RiskBand.LOW_RISK, score=0.10)
        self.assertEqual(dec, DecisionEnum.APPROVED)
        self.assertEqual(act, ActionEnum.APPROVE)
        
        # Medium risk low amount -> Step-Up Challenge
        dec, act = self.policy.resolve_decision_and_action(req_tf, RiskBand.MEDIUM_RISK, score=0.95)
        self.assertEqual(dec, DecisionEnum.CHALLENGED)
        self.assertEqual(act, ActionEnum.STEP_UP_CHALLENGE)
        
        # High risk -> Decline
        dec, act = self.policy.resolve_decision_and_action(req_tf, RiskBand.HIGH_RISK, score=0.995)
        self.assertEqual(dec, DecisionEnum.DECLINED)
        self.assertEqual(act, ActionEnum.DECLINE)

if __name__ == "__main__":
    unittest.main()
