"""
Risk Sentinel — Master Risk Decision Engine (Core Service)
Orchestrates the 10-stage synchronous decision pipeline within the 35ms latency budget.
"""

import time
import uuid
from typing import Dict, Any, Tuple, Optional

from src.engine.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    EngineMetadata,
    RiskBand,
    DecisionEnum,
    ActionEnum
)
from src.engine.model_manager import ModelManager
from src.engine.feature_pipeline import FeaturePipeline
from src.engine.state_store import BaseStateStore, InMemoryStateStore, StateStoreCircuitBreaker
from src.engine.explanation_resolver import ExplanationResolver
from src.engine.policy_engine import PolicyEngine
from src.engine.audit_logger import AuditLogger

class RiskDecisionEngine:
    def __init__(
        self,
        model_manager: Optional[ModelManager] = None,
        state_store: Optional[BaseStateStore] = None,
        state_timeout_ms: float = 15.0,
        policy_engine: Optional[PolicyEngine] = None,
        explanation_resolver: Optional[ExplanationResolver] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        self.model_manager = model_manager or ModelManager()
        self.state_store = state_store or InMemoryStateStore()
        self.circuit_breaker = StateStoreCircuitBreaker(self.state_store, timeout_ms=state_timeout_ms)
        self.feature_pipeline = FeaturePipeline()
        self.explanation_resolver = explanation_resolver or ExplanationResolver()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_logger = audit_logger or AuditLogger()
        
        self.engine_version = "v2.8.0-prod"
        self.model_version = self.model_manager.manifest.get("model_b", {}).get("model_id", "v1.0.0-HGB")
        self.policy_version = self.policy_engine.policy_version
        self.operating_threshold = self.policy_engine.threshold_high

    def evaluate(self, request_payload: Any) -> EvaluateResponse:
        """
        Executes the 10-stage synchronous transaction risk evaluation lifecycle.
        """
        t0 = time.time()
        
        # Stage 1: Input Validation & Schema Sanitization
        if isinstance(request_payload, dict):
            req = EvaluateRequest(**request_payload)
        elif isinstance(request_payload, EvaluateRequest):
            req = request_payload
        else:
            raise ValueError(f"Unsupported payload type: {type(request_payload)}")

        # Stage 2: Stateful Context Read (strictly < t) with Circuit Breaker Guard
        state_ctx, fallback_triggered, state_latency_ms = self.circuit_breaker.read_state_with_guard(
            req.nameOrig, req.nameDest
        )

        # Stage 3 & 4: Causal Feature Assembly & Model Inference Execution
        t_infer_0 = time.time()
        if fallback_triggered:
            # Fallback path: Model A (15-dim causal point-in-time baseline)
            X, feat_dict = self.feature_pipeline.build_features_a(req)
            risk_score = self.model_manager.predict_score_a(X)
            model_type_str = "MODEL_A_CAUSAL_BASELINE_FALLBACK"
            active_model_hash = self.model_manager.model_a_sha256
        else:
            # Primary path: Model B (21-dim stateful causal champion)
            X, feat_dict = self.feature_pipeline.build_features_b(req, state_ctx)
            risk_score = self.model_manager.predict_score_b(X)
            model_type_str = "MODEL_B_STATEFUL_HGB"
            active_model_hash = self.model_manager.model_b_sha256
        infer_latency_ms = (time.time() - t_infer_0) * 1000.0

        # Stage 5: Risk Score & Band Resolution
        risk_band = self.policy_engine.resolve_risk_band(risk_score)

        # Stage 6: Causal Explanation & Reason Generation
        reasons = self.explanation_resolver.resolve_explanations(
            req=req,
            score=risk_score,
            band=risk_band,
            state_ctx=state_ctx,
            fallback_active=fallback_triggered
        )

        # Stage 7: Policy & Action Resolution Engine
        decision, action = self.policy_engine.resolve_decision_and_action(
            req=req,
            band=risk_band,
            score=risk_score
        )

        # Stage 8: Stateful Entity Update (strictly post-decision)
        t_type = req.type.value if hasattr(req.type, 'value') else str(req.type)
        try:
            self.state_store.update_entity_state(
                sender_id=req.nameOrig,
                dest_id=req.nameDest,
                step=req.step,
                amount=req.amount,
                tx_type=t_type
            )
        except Exception:
            pass # Non-blocking on update error

        total_latency_ms = (time.time() - t0) * 1000.0

        # Stage 10: Synchronous Response Assembly
        metadata = EngineMetadata(
            engine_version=self.engine_version,
            model_version=self.model_version,
            model_type=model_type_str,
            policy_version=self.policy_version,
            operating_threshold=self.operating_threshold,
            fallback_triggered=fallback_triggered,
            execution_latency_ms=round(total_latency_ms, 3)
        )

        response = EvaluateResponse(
            transaction_id=req.transaction_id,
            evaluation_id=f"eval_{uuid.uuid4()}",
            risk_score=round(risk_score, 6),
            risk_band=risk_band,
            decision=decision,
            action=action,
            reasons=reasons,
            engine_metadata=metadata
        )

        # Stage 9: Immutable Audit Event Dispatch (Async / in-memory non-blocking)
        telemetry = {
            "execution_latency_ms": round(total_latency_ms, 3),
            "state_store_latency_ms": round(state_latency_ms, 3),
            "inference_latency_ms": round(infer_latency_ms, 3),
            "fallback_mode_active": fallback_triggered
        }
        self.audit_logger.record_decision(
            req=req,
            resp=response,
            model_hash=active_model_hash,
            feature_dict=feat_dict,
            telemetry=telemetry
        )

        return response
