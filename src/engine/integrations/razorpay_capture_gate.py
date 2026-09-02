"""
Risk Sentinel — Razorpay Test Mode Capture-Gate Integration
Phase 1 Implementation: Merchant-controlled post-authorization risk gate.
Evaluates authorized payments before executing manual capture.
Strictly decoupled, fail-closed, idempotent, and auditable.
"""

import os
import hmac
import hashlib
import json
import time
import uuid
import datetime
import urllib.request
import urllib.error
import base64
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from src.engine.schemas import EvaluateRequest, TransactionType, DecisionEnum, ActionEnum
from src.engine.decision_engine import RiskDecisionEngine

class RazorpayCaptureRequest(BaseModel):
    payment_id: str = Field(..., description="Razorpay payment identifier (pay_...)")
    order_id: Optional[str] = Field(default=None, description="Razorpay order identifier (order_...)")
    amount_paise: int = Field(..., ge=0, description="Transaction amount in paise (e.g. 50000 for 500 INR)")
    currency: str = Field(default="INR", description="3-letter currency code")
    status: str = Field(default="authorized", description="Payment status (must be 'authorized' for capture)")
    method: Optional[str] = Field(default="upi", description="Payment method (upi, card, netbanking, etc.)")
    vpa: Optional[str] = Field(default=None, description="Customer VPA if UPI payment")
    contact: Optional[str] = Field(default=None, description="Customer phone number")
    email: Optional[str] = Field(default=None, description="Customer email address")
    notes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Merchant context attached to payment")
    signature: Optional[str] = Field(default=None, description="HMAC-SHA256 signature if webhook-triggered")
    merchant_id: Optional[str] = Field(default="acc_test_merchant_01", description="Merchant account ID")
    raw_payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional raw payload for audit trace")

class CaptureGateResult(BaseModel):
    gate_event_id: str = Field(..., description="Unique identifier for this gate evaluation")
    timestamp_utc: str = Field(..., description="UTC timestamp of evaluation")
    payment_id: str = Field(..., description="Razorpay payment identifier")
    order_id: Optional[str] = Field(default=None, description="Razorpay order identifier")
    payment_status_before: str = Field(..., description="Payment state received by the gate")
    amount_inr: float = Field(..., description="Transaction amount in INR")
    currency: str = Field(default="INR")
    method: str = Field(default="unknown")
    customer_vpa: Optional[str] = None
    customer_contact_masked: Optional[str] = None
    merchant_id: str = Field(default="default_merchant")
    risk_evaluation_status: str = Field(..., description="EVALUATED_ENRICHED, INSUFFICIENT_FEATURES, ENGINE_ERROR, NON_AUTHORIZED_PAYMENT")
    risk_score: Optional[float] = Field(default=None, description="Operating risk score from frozen engine")
    decision: Optional[str] = Field(default=None, description="APPROVED, REVIEW_REQUIRED, DECLINED, NOT_EVALUATED")
    action: Optional[str] = Field(default=None, description="Policy action recommendation")
    primary_reason_code: Optional[str] = Field(default=None, description="Certified reason code from ExplanationResolver")
    reasons: Optional[Dict[str, Any]] = None
    capture_action: str = Field(..., description="CAPTURE_CALLED, CAPTURE_SUPPRESSED, CAPTURE_FAILED")
    capture_status: str = Field(..., description="CAPTURED, HELD_DECLINED, HELD_INSUFFICIENT_CONTEXT, HELD_NON_AUTHORIZED, HELD_FAIL_CLOSED, HELD_DUPLICATE")
    capture_api_response: Optional[Dict[str, Any]] = Field(default=None, description="Response from Razorpay Capture API or contract simulation")
    execution_mode: str = Field(..., description="LIVE_RAZORPAY_TEST_MODE or SIMULATED_CONTRACT_TEST_MODE")
    provenance: str = Field(..., description="RAZORPAY_TEST_MODE or RAZORPAY_COMPATIBLE_TEST_MODE")
    is_duplicate: bool = Field(default=False, description="Idempotency flag")
    integrity_hash: str = Field(..., description="SHA-256 chained integrity hash")
    audit_event_id: Optional[str] = Field(default=None, description="Chained engine audit event ID if evaluated")

def mask_contact(contact: Optional[str]) -> Optional[str]:
    if not contact:
        return None
    c = str(contact).strip()
    if len(c) <= 4:
        return "****"
    return f"{c[:2]}******{c[-2:]}"

class RazorpayCaptureGate:
    """
    Merchant-controlled Capture Gate for Razorpay Test Mode payments.
    Evaluates payments in 'authorized' state against the frozen RiskDecisionEngine.
    Enforces fail-closed capture, idempotency, and zero-fabrication context gating.
    """
    def __init__(
        self,
        engine: Optional[RiskDecisionEngine] = None,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None
    ):
        self.engine = engine
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")
        self.webhook_secret = webhook_secret or os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        
        # Test Mode enforcement: reject non-test keys to prevent live-mode accidents
        if self.key_id and not self.key_id.startswith("rzp_test_"):
            raise ValueError(f"Risk Sentinel operates exclusively in Razorpay Test Mode. Key '{self.key_id}' is not a test key (must start with 'rzp_test_').")
            
        self.has_live_credentials = bool(self.key_id and self.key_secret)
        self.processed_payments: Dict[str, CaptureGateResult] = {}
        self.gate_events_buffer: List[CaptureGateResult] = []
        self.max_buffer_size = 100
        self._last_gate_hash = "0" * 64

    def verify_signature(self, raw_body: bytes, signature_header: Optional[str]) -> bool:
        """Verifies HMAC-SHA256 signature if webhook-delivered."""
        if not self.webhook_secret:
            return True
        if not signature_header:
            return False
        expected_sig = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature_header.strip())

    def _compute_chained_gate_hash(self, prev_hash: str, payload_dict: Dict[str, Any]) -> str:
        serialized = json.dumps(payload_dict, sort_keys=True, default=str)
        return hashlib.sha256(f"{prev_hash}:{serialized}".encode("utf-8")).hexdigest()

    def _call_razorpay_capture_api(self, payment_id: str, amount_paise: int, currency: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Executes payment capture against Razorpay Payments API.
        If live credentials exist, calls POST https://api.razorpay.com/v1/payments/{id}/capture.
        If credentials are not configured, executes contract-compliant simulated test mode.
        """
        if self.has_live_credentials:
            url = f"https://api.razorpay.com/v1/payments/{payment_id}/capture"
            payload = json.dumps({"amount": amount_paise, "currency": currency}).encode("utf-8")
            auth_str = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode("utf-8")).decode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_str}"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    return True, resp_data
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                try:
                    err_json = json.loads(err_body)
                except Exception:
                    err_json = {"error": err_body}
                return False, {"http_code": e.code, "error": err_json}
            except Exception as e:
                return False, {"error": str(e)}
        else:
            # Contract-accurate simulated test mode execution
            simulated_response = {
                "id": payment_id,
                "entity": "payment",
                "amount": amount_paise,
                "currency": currency,
                "status": "captured",
                "order_id": None,
                "captured": True,
                "simulated": True,
                "notice": "Simulated Razorpay Test Mode Capture API Response (RAZORPAY_KEY_ID not configured in environment)."
            }
            return True, simulated_response

    def evaluate_and_capture(self, request: RazorpayCaptureRequest) -> CaptureGateResult:
        """
        Main Capture Gate workflow:
        1. Validate payment status is 'authorized'.
        2. Idempotency check.
        3. Zero-fabrication context check.
        4. Frozen engine evaluation.
        5. Fail-closed capture decision.
        6. Cryptographic block hashing & audit recording.
        """
        t_recv = datetime.datetime.now(datetime.timezone.utc).isoformat()
        gate_event_id = f"gate_evt_{uuid.uuid4().hex[:12]}"
        amount_inr = request.amount_paise / 100.0

        # Determine execution mode and provenance
        exec_mode = "LIVE_RAZORPAY_TEST_MODE" if self.has_live_credentials else "SIMULATED_CONTRACT_TEST_MODE"
        prov = "RAZORPAY_TEST_MODE" if self.has_live_credentials else "RAZORPAY_COMPATIBLE_TEST_MODE"

        # 1. State Validation: Only 'authorized' payments are eligible for capture
        if request.status.lower() != "authorized":
            result = CaptureGateResult(
                gate_event_id=gate_event_id,
                timestamp_utc=t_recv,
                payment_id=request.payment_id,
                order_id=request.order_id,
                payment_status_before=request.status,
                amount_inr=amount_inr,
                currency=request.currency,
                method=request.method or "unknown",
                customer_vpa=request.vpa,
                customer_contact_masked=mask_contact(request.contact),
                merchant_id=request.merchant_id or "default_merchant",
                risk_evaluation_status="NON_AUTHORIZED_PAYMENT",
                risk_score=None,
                decision="NOT_EVALUATED",
                action=None,
                primary_reason_code=None,
                reasons=None,
                capture_action="CAPTURE_SUPPRESSED",
                capture_status="HELD_NON_AUTHORIZED",
                capture_api_response={"reason": f"Payment is in '{request.status}' state, not 'authorized'. Capture cannot be called."},
                execution_mode=exec_mode,
                provenance=prov,
                is_duplicate=False,
                integrity_hash="0" * 64,
                audit_event_id=None
            )
            audit_dict = {
                "gate_event_id": gate_event_id,
                "payment_id": request.payment_id,
                "status": request.status,
                "capture_status": result.capture_status
            }
            result.integrity_hash = self._compute_chained_gate_hash(self._last_gate_hash, audit_dict)
            self._last_gate_hash = result.integrity_hash
            self.gate_events_buffer.insert(0, result)
            return result

        # 2. Idempotency Check: Prevent duplicate capture on replay
        if request.payment_id in self.processed_payments:
            cached = self.processed_payments[request.payment_id]
            dup = cached.model_copy(update={"is_duplicate": True})
            return dup

        # 3. Context Inspection (Zero-Fabrication Mandate)
        notes = request.notes or {}
        has_enriched_context = (
            "oldbalanceOrg" in notes and
            "oldbalanceDest" in notes and
            "step" in notes and
            "type" in notes
        )

        risk_score = None
        decision = None
        action = None
        reasons_dict = None
        primary_reason = None
        audit_event_id = None
        eval_status = None

        if not has_enriched_context:
            # FAIL CLOSED: Missing required banking context, never fabricate values
            eval_status = "INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION"
            decision = "NOT_EVALUATED"
            action = "HOLD_NO_CAPTURE"
            capture_action = "CAPTURE_SUPPRESSED"
            capture_status = "HELD_INSUFFICIENT_CONTEXT"
            capture_api_resp = {
                "status": "held",
                "reason": "Payment held. Missing pre-transaction balance context in merchant notes (zero-fabrication policy)."
            }
        else:
            # 4. Enriched Risk Sentinel Evaluation via Frozen Engine
            try:
                step_val = int(notes["step"])
                t_type = str(notes["type"]).upper()
                old_orig = float(notes["oldbalanceOrg"])
                old_dest = float(notes["oldbalanceDest"])
                sender_id = str(notes.get("nameOrig", request.contact or request.email or "C_RAZORPAY_SENDER"))
                dest_id = str(notes.get("nameDest", request.vpa or request.merchant_id or "M_RAZORPAY_MERCHANT"))

                eval_req = EvaluateRequest(
                    transaction_id=f"tx_{request.payment_id}",
                    step=step_val,
                    type=TransactionType(t_type),
                    amount=amount_inr,
                    nameOrig=sender_id,
                    oldbalanceOrg=old_orig,
                    nameDest=dest_id,
                    oldbalanceDest=old_dest,
                    merchant_id=request.merchant_id or "default_merchant"
                )

                if self.engine:
                    resp = self.engine.evaluate(eval_req)
                    risk_score = resp.risk_score
                    decision = resp.decision.value
                    action = resp.action.value
                    reasons_dict = resp.reasons.model_dump()
                    primary_reason = resp.reasons.primary_code
                    audit_event_id = resp.evaluation_id
                    eval_status = "EVALUATED_ENRICHED_TEST_MODE"
                else:
                    eval_status = "ENGINE_UNAVAILABLE"
                    decision = "DECLINED"
                    action = "DECLINE"
            except Exception as e:
                # FAIL CLOSED on any evaluation error
                eval_status = "ENGINE_ERROR"
                decision = "DECLINED"
                action = "DECLINE"
                capture_action = "CAPTURE_SUPPRESSED"
                capture_status = "HELD_FAIL_CLOSED"
                capture_api_resp = {"error": f"Risk evaluation error: {str(e)}"}

            # 5. Capture-Gate Decision Logic
            if eval_status == "EVALUATED_ENRICHED_TEST_MODE":
                if decision == "APPROVED":
                    # APPROVE -> Execute Capture API
                    capture_success, api_resp = self._call_razorpay_capture_api(
                        payment_id=request.payment_id,
                        amount_paise=request.amount_paise,
                        currency=request.currency
                    )
                    if capture_success:
                        capture_action = "CAPTURE_CALLED"
                        capture_status = "CAPTURED"
                        capture_api_resp = api_resp
                    else:
                        capture_action = "CAPTURE_FAILED"
                        capture_status = "HELD_CAPTURE_API_ERROR"
                        capture_api_resp = api_resp
                else:
                    # HOLD / DECLINE -> Capture is strictly NOT called
                    capture_action = "CAPTURE_SUPPRESSED"
                    capture_status = "HELD_DECLINED" if decision == "DECLINED" else "HELD_REVIEW_REQUIRED"
                    capture_api_resp = {
                        "status": "held",
                        "reason": f"Payment capture suppressed due to {decision} risk decision (Score: {risk_score})."
                    }

        # 6. Cryptographic Block Chaining
        audit_dict = {
            "gate_event_id": gate_event_id,
            "timestamp_utc": t_recv,
            "payment_id": request.payment_id,
            "amount_inr": amount_inr,
            "payment_status_before": request.status,
            "risk_evaluation_status": eval_status,
            "risk_score": risk_score,
            "decision": decision,
            "capture_action": capture_action,
            "capture_status": capture_status,
            "execution_mode": exec_mode
        }
        integrity_hash = self._compute_chained_gate_hash(self._last_gate_hash, audit_dict)
        self._last_gate_hash = integrity_hash

        result = CaptureGateResult(
            gate_event_id=gate_event_id,
            timestamp_utc=t_recv,
            payment_id=request.payment_id,
            order_id=request.order_id,
            payment_status_before=request.status,
            amount_inr=amount_inr,
            currency=request.currency,
            method=request.method or "unknown",
            customer_vpa=request.vpa,
            customer_contact_masked=mask_contact(request.contact),
            merchant_id=request.merchant_id or "default_merchant",
            risk_evaluation_status=eval_status,
            risk_score=risk_score,
            decision=decision,
            action=action,
            primary_reason_code=primary_reason,
            reasons=reasons_dict,
            capture_action=capture_action,
            capture_status=capture_status,
            capture_api_response=capture_api_resp,
            execution_mode=exec_mode,
            provenance=prov,
            is_duplicate=False,
            integrity_hash=integrity_hash,
            audit_event_id=audit_event_id
        )

        # 7. Store in Idempotency Map & Event Buffer
        self.processed_payments[request.payment_id] = result
        self.gate_events_buffer.insert(0, result)
        if len(self.gate_events_buffer) > self.max_buffer_size:
            self.gate_events_buffer.pop()

        return result

    def get_recent_gate_events(self, limit: int = 50) -> List[CaptureGateResult]:
        """Returns the most recent capture gate events."""
        return self.gate_events_buffer[:limit]
