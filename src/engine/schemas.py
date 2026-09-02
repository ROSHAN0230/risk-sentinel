"""
Risk Sentinel — Schema & Contract Definitions (Pydantic v2 Models)
Enforces strict input validation, response serialization, and audit schemas.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
import uuid
import datetime

class TransactionType(str, Enum):
    TRANSFER = "TRANSFER"
    CASH_OUT = "CASH_OUT"
    PAYMENT = "PAYMENT"
    CASH_IN = "CASH_IN"
    DEBIT = "DEBIT"

class RiskBand(str, Enum):
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"

class DecisionEnum(str, Enum):
    APPROVED = "APPROVED"
    CHALLENGED = "CHALLENGED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DECLINED = "DECLINED"

class ActionEnum(str, Enum):
    APPROVE = "APPROVE"
    STEP_UP_CHALLENGE = "STEP_UP_CHALLENGE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    DECLINE = "DECLINE"

class EvaluateRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique UUID transaction identifier")
    step: int = Field(..., ge=1, description="Discrete simulation or epoch hour step (>=1)")
    type: TransactionType = Field(..., description="Transaction channel type")
    amount: float = Field(..., gt=0.0, description="Transaction monetary amount (must be strictly positive)")
    nameOrig: str = Field(..., min_length=1, max_length=128, description="Sender account identifier")
    oldbalanceOrg: float = Field(..., ge=0.0, description="Sender point-in-time balance prior to execution")
    nameDest: str = Field(..., min_length=1, max_length=128, description="Destination account identifier")
    oldbalanceDest: float = Field(..., ge=0.0, description="Destination point-in-time balance prior to execution")
    merchant_id: Optional[str] = Field(default="default_merchant", description="Merchant account ID")

    @field_validator("amount")
    @classmethod
    def validate_amount_finite(cls, v: float) -> float:
        if not (v > 0.0) or float("inf") == v or v != v:
            raise ValueError("Amount must be a finite positive number.")
        return float(v)

    @field_validator("oldbalanceOrg", "oldbalanceDest")
    @classmethod
    def validate_balance_non_negative(cls, v: float) -> float:
        if v < 0.0 or float("inf") == v or v != v:
            raise ValueError("Balance must be a finite non-negative number.")
        return float(v)

class ReasonDetails(BaseModel):
    primary_code: str
    all_codes: List[str]
    narrative: str
    causal_evidence: Dict[str, Any]

class EngineMetadata(BaseModel):
    engine_version: str = "v2.8.0-prod"
    model_version: str = "v1.0.0-HGB"
    model_type: str
    policy_version: str = "v1.2.0-frozen"
    operating_threshold: float = 0.990
    fallback_triggered: bool = False
    execution_latency_ms: float

class EvaluateResponse(BaseModel):
    transaction_id: str
    evaluation_id: str = Field(default_factory=lambda: f"eval_{uuid.uuid4()}")
    timestamp_iso: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    risk_score: float
    risk_band: RiskBand
    decision: DecisionEnum
    action: ActionEnum
    reasons: ReasonDetails
    engine_metadata: EngineMetadata

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4()}")
    event_timestamp_utc: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    transaction_id: str
    merchant_id: str
    lineage: Dict[str, Any]
    runtime_telemetry: Dict[str, Any]
    input_snapshot_masked: Dict[str, Any]
    causal_features_extracted: Dict[str, Any]
    evaluation_result: Dict[str, Any]
    integrity_hash: str
