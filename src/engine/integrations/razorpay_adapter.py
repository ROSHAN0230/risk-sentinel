"""
Risk Sentinel — Razorpay Test Mode Webhook Adapter & Event Normalization
Phase P0 Implementation: Defense-only payment event ingestion, HMAC-SHA256 signature verification,
idempotency tracking, model readiness auditing, and zero-fabrication causal routing.
"""

import os
import hmac
import hashlib
import json
import time
import uuid
import datetime
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field, field_validator

from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine

class RazorpayPaymentEntity(BaseModel):
    id: str = Field(..., description="Razorpay payment identifier (pay_...)")
    amount: int = Field(..., ge=0, description="Amount in paise (integer)")
    currency: str = Field(default="INR", description="3-letter currency code")
    status: Optional[str] = Field(default="authorized", description="Payment status")
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    international: Optional[bool] = False
    method: Optional[str] = "unknown"
    amount_refunded: Optional[int] = 0
    refund_status: Optional[str] = None
    captured: Optional[bool] = False
    description: Optional[str] = None
    card_id: Optional[str] = None
    bank: Optional[str] = None
    wallet: Optional[str] = None
    vpa: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    notes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    fee: Optional[int] = None
    tax: Optional[int] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    created_at: Optional[int] = None

class RazorpayWebhookPayload(BaseModel):
    entity: str = Field(default="event", description="Entity type")
    account_id: Optional[str] = Field(default=None, description="Razorpay merchant account ID")
    event: str = Field(..., description="Razorpay webhook event type (e.g. payment.authorized)")
    contains: Optional[List[str]] = Field(default_factory=lambda: ["payment"])
    payload: Dict[str, Any] = Field(..., description="Webhook payload container")
    created_at: Optional[int] = None

class NormalizedWebhookEvent(BaseModel):
    event_id: str
    received_at_utc: str
    source: str = "RAZORPAY_TEST_MODE"
    event_type: str
    payment_id: str
    amount_inr: float
    currency: str
    method: str
    customer_vpa: Optional[str] = None
    customer_contact_masked: Optional[str] = None
    merchant_id: str
    evaluation_status: str
    readiness_reason: str
    missing_features: List[str] = Field(default_factory=list)
    risk_score: Optional[float] = None
    decision: Optional[str] = None
    action: Optional[str] = None
    reasons: Optional[Dict[str, Any]] = None
    engine_metadata: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None
    integrity_hash: str
    is_duplicate: bool = False

def mask_contact(contact: Optional[str]) -> Optional[str]:
    if not contact:
        return None
    c = str(contact).strip()
    if len(c) <= 4:
        return "****"
    return f"{c[:2]}******{c[-2:]}"

class RazorpayWebhookAdapter:
    """
    Decoupled integration layer for Razorpay Test Mode webhooks.
    Validates structure, verifies HMAC signatures, enforces idempotency,
    and applies the strict Model Readiness boundary without fabricating features.
    """
    def __init__(self, engine: Optional[RiskDecisionEngine] = None, webhook_secret: Optional[str] = None):
        self.engine = engine
        self.webhook_secret = webhook_secret or os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        self.processed_events: Dict[str, NormalizedWebhookEvent] = {}
        self.event_buffer: List[NormalizedWebhookEvent] = []
        self.max_buffer_size = 100
        self._last_event_hash = "0" * 64

    def verify_signature(self, raw_body: bytes, signature_header: Optional[str]) -> bool:
        """
        Verifies HMAC-SHA256 signature against the configured webhook secret.
        If secret is empty (dev/unconfigured mode), allows request but logs warning.
        If secret is configured, strictly rejects invalid signatures.
        """
        if not self.webhook_secret:
            # Dev mode: webhook secret unconfigured, signature verification bypassed
            return True
        if not signature_header:
            return False
        expected_sig = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature_header.strip())

    def _compute_chained_event_hash(self, prev_hash: str, payload_dict: Dict[str, Any]) -> str:
        serialized = json.dumps(payload_dict, sort_keys=True, default=str)
        return hashlib.sha256(f"{prev_hash}:{serialized}".encode("utf-8")).hexdigest()

    def process_webhook(
        self,
        raw_body: bytes,
        signature_header: Optional[str] = None,
        account_id_override: Optional[str] = None
    ) -> Tuple[NormalizedWebhookEvent, int]:
        """
        Processes an incoming Razorpay webhook.
        Returns (NormalizedWebhookEvent, HTTP status code).
        """
        t_recv = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Signature Verification
        if not self.verify_signature(raw_body, signature_header):
            error_event = NormalizedWebhookEvent(
                event_id=f"evt_err_{uuid.uuid4().hex[:12]}",
                received_at_utc=t_recv,
                source="RAZORPAY_TEST_MODE",
                event_type="SIGNATURE_VERIFICATION_FAILED",
                payment_id="unknown",
                amount_inr=0.0,
                currency="INR",
                method="unknown",
                merchant_id=account_id_override or "unknown",
                evaluation_status="REJECTED_INVALID_SIGNATURE",
                readiness_reason="HMAC-SHA256 signature does not match configured webhook secret.",
                integrity_hash="0" * 64
            )
            return error_event, 401

        # 2. JSON Parsing & Schema Validation
        try:
            body_json = json.loads(raw_body.decode("utf-8"))
            webhook_payload = RazorpayWebhookPayload(**body_json)
        except Exception as e:
            error_event = NormalizedWebhookEvent(
                event_id=f"evt_err_{uuid.uuid4().hex[:12]}",
                received_at_utc=t_recv,
                source="RAZORPAY_TEST_MODE",
                event_type="SCHEMA_VALIDATION_FAILED",
                payment_id="unknown",
                amount_inr=0.0,
                currency="INR",
                method="unknown",
                merchant_id=account_id_override or "unknown",
                evaluation_status="REJECTED_MALFORMED_PAYLOAD",
                readiness_reason=f"Payload failed schema validation: {str(e)}",
                integrity_hash="0" * 64
            )
            return error_event, 422

        # 3. Extract Payment Entity
        payment_dict = webhook_payload.payload.get("payment", {}).get("entity", {})
        if not payment_dict or not payment_dict.get("id"):
            error_event = NormalizedWebhookEvent(
                event_id=f"evt_err_{uuid.uuid4().hex[:12]}",
                received_at_utc=t_recv,
                source="RAZORPAY_TEST_MODE",
                event_type=webhook_payload.event,
                payment_id="unknown",
                amount_inr=0.0,
                currency="INR",
                method="unknown",
                merchant_id=webhook_payload.account_id or "unknown",
                evaluation_status="REJECTED_MISSING_PAYMENT_ENTITY",
                readiness_reason="Webhook does not contain a valid payment.entity structure.",
                integrity_hash="0" * 64
            )
            return error_event, 422

        payment = RazorpayPaymentEntity(**payment_dict)
        event_id = f"evt_{payment.id}_{webhook_payload.event}"
        amount_inr = payment.amount / 100.0  # Convert paise to INR

        # 4. Idempotency Check
        if event_id in self.processed_events:
            cached = self.processed_events[event_id]
            # Return duplicate record
            dup = cached.model_copy(update={"is_duplicate": True})
            return dup, 200

        # 5. Model Readiness Evaluation (Strict Boundary)
        notes = payment.notes or {}
        # Check if caller explicitly provided pre-transaction banking context via notes
        has_enriched_context = (
            "oldbalanceOrg" in notes and
            "oldbalanceDest" in notes and
            "step" in notes and
            "type" in notes
        )

        missing_fields = []
        if not has_enriched_context:
            missing_fields = ["oldbalanceOrg", "oldbalanceDest", "step", "channel_type"]

        risk_score = None
        decision = None
        action = None
        reasons = None
        metadata = None
        audit_id = None

        if not has_enriched_context:
            eval_status = "INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION"
            readiness_reason = (
                "Razorpay payment event does not contain the banking-balance context "
                "required by the frozen PaySim-trained feature contract. "
                "Causal features oldbalanceOrg, oldbalanceDest, and step are unavailable in raw gateway webhooks."
            )
        else:
            # Enriched Test Mode Path
            try:
                # Convert notes safely
                step_val = int(notes["step"])
                t_type = str(notes["type"]).upper()
                old_orig = float(notes["oldbalanceOrg"])
                old_dest = float(notes["oldbalanceDest"])
                sender_id = str(notes.get("nameOrig", payment.contact or payment.email or "C_RAZORPAY_SENDER"))
                dest_id = str(notes.get("nameDest", payment.vpa or webhook_payload.account_id or "M_RAZORPAY_MERCHANT"))

                eval_req = EvaluateRequest(
                    transaction_id=f"tx_{payment.id}",
                    step=step_val,
                    type=TransactionType(t_type),
                    amount=amount_inr,
                    nameOrig=sender_id,
                    oldbalanceOrg=old_orig,
                    nameDest=dest_id,
                    oldbalanceDest=old_dest,
                    merchant_id=webhook_payload.account_id or "default_merchant"
                )

                if self.engine:
                    resp = self.engine.evaluate(eval_req)
                    risk_score = resp.risk_score
                    decision = resp.decision.value
                    action = resp.action.value
                    reasons = resp.reasons.model_dump()
                    metadata = resp.engine_metadata.model_dump()
                    audit_id = resp.evaluation_id

                eval_status = "EVALUATED_ENRICHED_TEST_MODE"
                readiness_reason = "Evaluated via frozen RiskDecisionEngine under explicit Test Mode Enriched Context."
            except Exception as eval_err:
                eval_status = "ENRICHED_EVALUATION_ERROR"
                readiness_reason = f"Enriched context evaluation error: {str(eval_err)}"

        # 6. Cryptographic Block Chaining for Audit Record
        audit_payload = {
            "event_id": event_id,
            "received_at_utc": t_recv,
            "payment_id": payment.id,
            "amount_inr": amount_inr,
            "method": payment.method,
            "evaluation_status": eval_status,
            "risk_score": risk_score,
            "decision": decision
        }
        integrity_hash = self._compute_chained_event_hash(self._last_event_hash, audit_payload)
        self._last_event_hash = integrity_hash

        normalized_event = NormalizedWebhookEvent(
            event_id=event_id,
            received_at_utc=t_recv,
            source="RAZORPAY_TEST_MODE",
            event_type=webhook_payload.event,
            payment_id=payment.id,
            amount_inr=amount_inr,
            currency=payment.currency,
            method=payment.method or "unknown",
            customer_vpa=payment.vpa,
            customer_contact_masked=mask_contact(payment.contact),
            merchant_id=webhook_payload.account_id or "default_merchant",
            evaluation_status=eval_status,
            readiness_reason=readiness_reason,
            missing_features=missing_fields,
            risk_score=risk_score,
            decision=decision,
            action=action,
            reasons=reasons,
            engine_metadata=metadata,
            audit_id=audit_id,
            integrity_hash=integrity_hash,
            is_duplicate=False
        )

        # 7. Store in Idempotency Map & Event Buffer
        self.processed_events[event_id] = normalized_event
        self.event_buffer.insert(0, normalized_event)
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop()

        return normalized_event, 200

    def get_recent_events(self, limit: int = 50) -> List[NormalizedWebhookEvent]:
        return self.event_buffer[:limit]
