"""
Risk Sentinel — Immutable Decision Audit Logger
Dispatches cryptographically chained audit events with PII masking and lineage tracking.
"""

import hashlib
import json
import threading
import uuid
import datetime
from typing import Dict, Any, List, Optional
from src.engine.schemas import (
    AuditEvent,
    EvaluateRequest,
    EvaluateResponse,
    RiskBand,
    DecisionEnum,
    ActionEnum
)

def mask_account_id(account_id: str) -> str:
    """Masks customer/account identifiers for privacy (e.g. C123456789 -> C123***789)."""
    if len(account_id) <= 6:
        return account_id[:2] + "***"
    return account_id[:4] + "***" + account_id[-3:]

class AuditLogger:
    def __init__(self, buffer_size: int = 10000):
        self._lock = threading.Lock()
        self.buffer_size = buffer_size
        self.events: List[AuditEvent] = []
        self._last_block_hash = "GENESIS_BLOCK_0000000000000000000000000000000000000000000000000000"

    def _compute_chained_hash(self, prev_hash: str, payload_dict: Dict[str, Any]) -> str:
        serialized = json.dumps(payload_dict, sort_keys=True)
        sha = hashlib.sha256()
        sha.update(prev_hash.encode('utf-8'))
        sha.update(serialized.encode('utf-8'))
        return sha.hexdigest()

    def record_decision(
        self,
        req: EvaluateRequest,
        resp: EvaluateResponse,
        model_hash: str,
        feature_dict: Dict[str, float],
        telemetry: Dict[str, Any]
    ) -> AuditEvent:
        event_id = f"aud_{uuid.uuid4()}"
        timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        lineage = {
            "engine_version": resp.engine_metadata.engine_version,
            "model_version": resp.engine_metadata.model_version,
            "model_type": resp.engine_metadata.model_type,
            "model_artifact_hash": model_hash,
            "policy_version": resp.engine_metadata.policy_version,
            "operating_threshold": resp.engine_metadata.operating_threshold
        }
        
        input_snapshot_masked = {
            "step": req.step,
            "type": req.type.value if hasattr(req.type, 'value') else str(req.type),
            "amount": req.amount,
            "sender_masked": mask_account_id(req.nameOrig),
            "sender_old_balance": req.oldbalanceOrg,
            "dest_masked": mask_account_id(req.nameDest),
            "dest_old_balance": req.oldbalanceDest
        }
        
        eval_result = {
            "raw_model_score": resp.risk_score,
            "risk_band": resp.risk_band.value if hasattr(resp.risk_band, 'value') else str(resp.risk_band),
            "decision": resp.decision.value if hasattr(resp.decision, 'value') else str(resp.decision),
            "action": resp.action.value if hasattr(resp.action, 'value') else str(resp.action),
            "primary_reason_code": resp.reasons.primary_code,
            "all_reason_codes": resp.reasons.all_codes
        }
        
        payload_for_hash = {
            "event_id": event_id,
            "timestamp_utc": timestamp_utc,
            "transaction_id": req.transaction_id,
            "merchant_id": req.merchant_id,
            "lineage": lineage,
            "telemetry": telemetry,
            "features": feature_dict,
            "result": eval_result
        }
        
        with self._lock:
            integrity_hash = self._compute_chained_hash(self._last_block_hash, payload_for_hash)
            self._last_block_hash = integrity_hash
            
            event = AuditEvent(
                event_id=event_id,
                event_timestamp_utc=timestamp_utc,
                transaction_id=req.transaction_id,
                merchant_id=req.merchant_id,
                lineage=lineage,
                runtime_telemetry=telemetry,
                input_snapshot_masked=input_snapshot_masked,
                causal_features_extracted=feature_dict,
                evaluation_result=eval_result,
                integrity_hash=integrity_hash
            )
            
            self.events.append(event)
            if len(self.events) > self.buffer_size:
                self.events.pop(0)
                
            return event

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [e.model_dump() for e in self.events[-limit:]]

    def clear(self) -> None:
        with self._lock:
            self.events.clear()
            self._last_block_hash = "GENESIS_BLOCK_0000000000000000000000000000000000000000000000000000"
