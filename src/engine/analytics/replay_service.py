"""
Risk Sentinel — Phase 2 Fraud Decision Replay Service
Provides isolated, ephemeral execution of the frozen Risk Sentinel decision engine.
Enables judges and risk officers to modify transaction and behavioral inputs,
observing real-time shifts across Features -> Score -> Reasons -> Policy -> Decision -> Economics.
Strictly isolated: zero production state mutation, zero audit ledger pollution, zero gateway capture.
"""

import uuid
import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.state_store import InMemoryStateStore
from src.engine.audit_logger import AuditLogger

class SandboxContext(BaseModel):
    dest_unique_orig_cnt: Optional[int] = Field(default=None, ge=0, description="Destination mule fan-in unique senders count")
    sender_prev_in_tx_cnt: Optional[int] = Field(default=None, ge=0, description="Sender historical inbound transaction count")
    is_sender_cold_start: Optional[bool] = Field(default=None, description="Force sender cold-start (zero prior history)")

class ReplayRequest(BaseModel):
    baseline_fixture_id: Optional[str] = Field(default=None, description="Optional ID of baseline fixture (e.g. DEMO-03)")
    step: int = Field(default=450, ge=1, description="Discrete simulation step hour (>=1)")
    type: str = Field(default="TRANSFER", description="Transaction channel type (TRANSFER, CASH_OUT, PAYMENT, etc.)")
    amount: float = Field(..., gt=0.0, description="Transaction monetary amount")
    nameOrig: str = Field(default="C_REPLAY_SENDER", min_length=1, max_length=128)
    oldbalanceOrg: float = Field(..., ge=0.0, description="Sender pre-transaction balance")
    nameDest: str = Field(default="C_REPLAY_DEST", min_length=1, max_length=128)
    oldbalanceDest: float = Field(default=0.0, ge=0.0, description="Destination pre-transaction balance")
    merchant_id: Optional[str] = Field(default="default_merchant")
    sandbox_context: Optional[SandboxContext] = Field(default_factory=SandboxContext)
    alpha: float = Field(default=0.010, ge=0.001, le=0.050, description="Intervention friction factor (0.001 to 0.050)")

class ReplayFeatureSnapshot(BaseModel):
    amount: float
    oldbalanceOrg: float
    oldbalanceDest: float
    orig_balance_drain_ratio: float
    amount_to_orig_bal: float
    dest_unique_orig_cnt: float
    is_sender_cold_start: float

class ReplayEvaluation(BaseModel):
    model_type: str
    operating_score: float
    score_interpretation: str = "Operating decision score derived from validation class-weight shift"
    risk_band: str
    decision: str
    action: str
    primary_reason_code: str
    all_reason_codes: List[str]
    narrative: str
    features: Dict[str, float]

class ReplayEconomicImpact(BaseModel):
    alpha: float
    alpha_percentage: str
    disclaimer: str = "Analytical scenario sensitivity — not Razorpay unit economics."
    decision_outcome: str
    hypothetical_fraud_exposure: float
    hypothetical_friction_cost: float
    economic_narrative: str

class ReplayDelta(BaseModel):
    score_delta: float
    decision_changed: bool
    reason_code_changed: bool
    baseline_decision: str
    replay_decision: str
    baseline_reason: str
    replay_reason: str
    features_diff: Dict[str, Dict[str, float]]

class ReplayResponse(BaseModel):
    replay_id: str
    timestamp_utc: str
    provenance: str = "EXPLORATORY_REPLAY — ZERO PRODUCTION MUTATION"
    baseline_fixture_id: Optional[str] = None
    replay_inputs: Dict[str, Any]
    replayed_evaluation: ReplayEvaluation
    baseline_evaluation: Optional[ReplayEvaluation] = None
    deltas: Optional[ReplayDelta] = None
    economic_impact: ReplayEconomicImpact

class EphemeralReplayAuditLogger(AuditLogger):
    """Null/Ephemeral logger that discards events to prevent polluting the production audit ledger."""
    def __init__(self):
        super().__init__(buffer_size=10)
        self.discarded_count = 0

    def record_decision(self, req, resp, model_hash, feature_dict, telemetry):
        self.discarded_count += 1
        return None

class ReplayService:
    """
    Isolated Fraud Decision Replay Service.
    Executes the real frozen inference, feature pipeline, explanation, and policy engines
    within an isolated ephemeral sandbox.
    """
    def __init__(self, prod_engine: RiskDecisionEngine):
        self.prod_engine = prod_engine

    def _create_sandbox_engine(self, sandbox_ctx: Optional[SandboxContext] = None, dest_id: Optional[str] = None, step: int = 450) -> Tuple[RiskDecisionEngine, InMemoryStateStore]:
        """Creates an ephemeral RiskDecisionEngine with an isolated state store and null audit logger."""
        sandbox_state_store = InMemoryStateStore()
        
        # Seed sandbox state store if specific behavioral knobs were supplied
        if sandbox_ctx and dest_id:
            if sandbox_ctx.dest_unique_orig_cnt is not None and sandbox_ctx.dest_unique_orig_cnt > 0:
                cnt = sandbox_ctx.dest_unique_orig_cnt
                senders_set = {f"C_SEED_MULE_SENDER_{i}" for i in range(cnt)}
                sandbox_state_store.dest_state[dest_id] = [cnt, 1000.0 * cnt, 1000.0, step - 1, senders_set]

        sandbox_engine = RiskDecisionEngine(
            model_manager=self.prod_engine.model_manager,
            state_store=sandbox_state_store,
            policy_engine=self.prod_engine.policy_engine,
            explanation_resolver=self.prod_engine.explanation_resolver,
            audit_logger=EphemeralReplayAuditLogger()
        )
        return sandbox_engine, sandbox_state_store

    def _extract_feature_summary(self, req: EvaluateRequest, state_ctx: Dict[str, Any]) -> Dict[str, float]:
        """Extracts key causal and behavioral feature values point-in-time."""
        drain_ratio = float(req.amount / (req.oldbalanceOrg + 1.0)) if req.oldbalanceOrg >= 0 else 0.0
        drain_ratio = min(max(drain_ratio, 0.0), 1.0)
        
        dest_cnt = 0.0
        if state_ctx and state_ctx.get("dest"):
            dest_cnt = float(len(state_ctx["dest"][4]))
            
        is_cold = 1.0 if (not state_ctx or not state_ctx.get("sender")) else 0.0

        return {
            "amount": req.amount,
            "oldbalanceOrg": req.oldbalanceOrg,
            "oldbalanceDest": req.oldbalanceDest,
            "orig_balance_drain_ratio": round(drain_ratio, 5),
            "amount_to_orig_bal": round(drain_ratio, 5),
            "dest_unique_orig_cnt": dest_cnt,
            "is_sender_cold_start": is_cold
        }

    def _calculate_economics(self, amount: float, decision: str, alpha: float) -> ReplayEconomicImpact:
        """Calculates analytical scenario sensitivity impact for the decision."""
        alpha_pct = f"{alpha * 100:.1f}%"
        if decision == "APPROVED":
            fraud_exp = amount
            fric_cost = 0.0
            narrative = (
                f"Transaction approved. If genuine fraud, hypothetical exposure is ${amount:,.2f} (scenario assumption). "
                f"If legitimate, merchant/customer friction cost is $0.00."
            )
        elif decision == "DECLINED":
            fraud_exp = 0.0
            fric_cost = round(alpha * amount, 2)
            narrative = (
                f"Transaction declined. If genuine fraud, ${amount:,.2f} in loss is prevented. "
                f"If legitimate, hypothetical merchant friction cost is ${fric_cost:,.2f} at alpha={alpha_pct}."
            )
        else: # REVIEW_REQUIRED / CHALLENGED
            fraud_exp = round(0.5 * amount, 2) # Provisional hold / step-up
            fric_cost = round(0.5 * alpha * amount, 2)
            narrative = (
                f"Transaction flagged for manual review. If genuine fraud, exposure is provisionally contained to ${fraud_exp:,.2f}. "
                f"Hypothetical challenge verification friction is ${fric_cost:,.2f} at alpha={alpha_pct}."
            )

        return ReplayEconomicImpact(
            alpha=alpha,
            alpha_percentage=alpha_pct,
            decision_outcome=decision,
            hypothetical_fraud_exposure=fraud_exp,
            hypothetical_friction_cost=fric_cost,
            economic_narrative=narrative
        )

    def evaluate_replay(self, request: ReplayRequest) -> ReplayResponse:
        """
        Executes an isolated decision replay with baseline diffing and economic analysis.
        Guaranteed zero mutation of production state_store or audit_logger.
        """
        replay_id = f"rpl_{uuid.uuid4().hex[:12]}"
        t_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Setup Sandbox Engine for Replayed Transaction
        sandbox_engine, _ = self._create_sandbox_engine(
            sandbox_ctx=request.sandbox_context,
            dest_id=request.nameDest,
            step=request.step
        )

        t_type = TransactionType(request.type.upper())
        eval_req = EvaluateRequest(
            transaction_id=f"tx_rpl_{replay_id[:8]}",
            step=request.step,
            type=t_type,
            amount=request.amount,
            nameOrig=request.nameOrig,
            oldbalanceOrg=request.oldbalanceOrg,
            nameDest=request.nameDest,
            oldbalanceDest=request.oldbalanceDest,
            merchant_id=request.merchant_id or "default_merchant"
        )

        # Read pre-execution state context (strictly < t) for point-in-time feature snapshot
        pre_state_ctx = sandbox_engine.state_store.read_entity_state(eval_req.nameOrig, eval_req.nameDest)
        replay_feat_summary = self._extract_feature_summary(eval_req, pre_state_ctx)

        # 2. Execute Replay Evaluation through Sandbox Engine
        resp = sandbox_engine.evaluate(eval_req)

        replayed_eval = ReplayEvaluation(
            model_type=resp.engine_metadata.model_type,
            operating_score=resp.risk_score,
            risk_band=resp.risk_band.value,
            decision=resp.decision.value,
            action=resp.action.value,
            primary_reason_code=resp.reasons.primary_code,
            all_reason_codes=resp.reasons.all_codes,
            narrative=resp.reasons.narrative,
            features=replay_feat_summary
        )

        # 3. Optional Baseline Evaluation (for diffing)
        baseline_eval = None
        deltas = None
        
        # If a baseline fixture ID was requested, evaluate baseline scenario in its own clean sandbox
        from src.engine.schemas import EvaluateRequest as EvReq
        baseline_req = None
        if request.baseline_fixture_id == "DEMO-03":
            baseline_req = EvReq(
                transaction_id="tx_baseline_demo03",
                step=452,
                type=TransactionType.TRANSFER,
                amount=284100.50,
                nameOrig="C_VICTIM_03",
                oldbalanceOrg=284100.50,
                nameDest="C_MULE_03",
                oldbalanceDest=0.0
            )
        elif request.baseline_fixture_id == "DEMO-01":
            baseline_req = EvReq(
                transaction_id="tx_baseline_demo01",
                step=450,
                type=TransactionType.PAYMENT,
                amount=84.50,
                nameOrig="C_CONSUMER_01",
                oldbalanceOrg=5000.0,
                nameDest="M_MERCHANT_01",
                oldbalanceDest=0.0
            )
        elif request.baseline_fixture_id == "DEMO-04":
            baseline_req = EvReq(
                transaction_id="tx_baseline_demo04",
                step=453,
                type=TransactionType.TRANSFER,
                amount=50.00,
                nameOrig="C_FRESH_USER_04",
                oldbalanceOrg=1000.00,
                nameDest="C_DEST_04",
                oldbalanceDest=200.00
            )

        if baseline_req:
            base_engine, _ = self._create_sandbox_engine(step=baseline_req.step)
            base_ctx = base_engine.state_store.read_entity_state(baseline_req.nameOrig, baseline_req.nameDest)
            base_feat_summary = self._extract_feature_summary(baseline_req, base_ctx)
            base_resp = base_engine.evaluate(baseline_req)

            baseline_eval = ReplayEvaluation(
                model_type=base_resp.engine_metadata.model_type,
                operating_score=base_resp.risk_score,
                risk_band=base_resp.risk_band.value,
                decision=base_resp.decision.value,
                action=base_resp.action.value,
                primary_reason_code=base_resp.reasons.primary_code,
                all_reason_codes=base_resp.reasons.all_codes,
                narrative=base_resp.reasons.narrative,
                features=base_feat_summary
            )

            # Compute deltas
            feat_diff = {}
            for k, v in replay_feat_summary.items():
                b_v = base_feat_summary.get(k, 0.0)
                feat_diff[k] = {"baseline": b_v, "replay": v, "delta": round(v - b_v, 5)}

            deltas = ReplayDelta(
                score_delta=round(replayed_eval.operating_score - baseline_eval.operating_score, 6),
                decision_changed=(replayed_eval.decision != baseline_eval.decision),
                reason_code_changed=(replayed_eval.primary_reason_code != baseline_eval.primary_reason_code),
                baseline_decision=baseline_eval.decision,
                replay_decision=replayed_eval.decision,
                baseline_reason=baseline_eval.primary_reason_code,
                replay_reason=replayed_eval.primary_reason_code,
                features_diff=feat_diff
            )

        # 4. Calculate Economic Scenario Impact
        econ_impact = self._calculate_economics(
            amount=request.amount,
            decision=replayed_eval.decision,
            alpha=request.alpha
        )

        return ReplayResponse(
            replay_id=replay_id,
            timestamp_utc=t_utc,
            provenance="EXPLORATORY_REPLAY — ZERO PRODUCTION MUTATION",
            baseline_fixture_id=request.baseline_fixture_id,
            replay_inputs={
                "step": request.step,
                "type": request.type,
                "amount": request.amount,
                "oldbalanceOrg": request.oldbalanceOrg,
                "oldbalanceDest": request.oldbalanceDest,
                "alpha": request.alpha
            },
            replayed_evaluation=replayed_eval,
            baseline_evaluation=baseline_eval,
            deltas=deltas,
            economic_impact=econ_impact
        )
