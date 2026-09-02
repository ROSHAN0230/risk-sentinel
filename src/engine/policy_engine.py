"""
Risk Sentinel — Policy Resolution Engine
Decouples statistical Risk Bands from Operational Decision Actions.
Implements locked threshold rules (θ_high = 0.990, θ_medium = 0.900) and channel policies.
"""

from typing import Tuple, Dict, Any, Optional
from src.engine.schemas import (
    TransactionType,
    RiskBand,
    DecisionEnum,
    ActionEnum,
    EvaluateRequest
)

class PolicyEngine:
    def __init__(
        self,
        threshold_high: float = 0.990,
        threshold_medium: float = 0.900,
        policy_version: str = "v1.2.0-frozen",
        enable_fast_path_bypass: bool = True
    ):
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium
        self.policy_version = policy_version
        self.enable_fast_path_bypass = enable_fast_path_bypass

    def resolve_risk_band(self, score: float) -> RiskBand:
        if score >= self.threshold_high:
            return RiskBand.HIGH_RISK
        elif score >= self.threshold_medium:
            return RiskBand.MEDIUM_RISK
        else:
            return RiskBand.LOW_RISK

    def resolve_decision_and_action(
        self,
        req: EvaluateRequest,
        band: RiskBand,
        score: float
    ) -> Tuple[DecisionEnum, ActionEnum]:
        t_type = req.type
        amt = float(req.amount)
        
        # 1. Fast-path empirical bypass for low-risk channels (FROZEN #032)
        if self.enable_fast_path_bypass and t_type in [TransactionType.PAYMENT, TransactionType.CASH_IN, TransactionType.DEBIT]:
            return DecisionEnum.APPROVED, ActionEnum.APPROVE
            
        # 2. Scored high-risk channels (TRANSFER, CASH_OUT)
        if band == RiskBand.LOW_RISK:
            return DecisionEnum.APPROVED, ActionEnum.APPROVE
            
        elif band == RiskBand.MEDIUM_RISK:
            # Low amount borderline -> Step-up challenge (2FA/OTP); High amount -> Manual review
            if amt < 50000.0:
                return DecisionEnum.CHALLENGED, ActionEnum.STEP_UP_CHALLENGE
            else:
                return DecisionEnum.REVIEW_REQUIRED, ActionEnum.MANUAL_REVIEW
                
        else: # HIGH_RISK
            return DecisionEnum.DECLINED, ActionEnum.DECLINE
