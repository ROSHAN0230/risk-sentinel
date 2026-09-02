# Risk Sentinel Audit Trail & Contract Specification
**Document ID**: `AUDIT-CTR-2.8-001`  
**Status**: `FROZEN SCHEMA CONTRACT`  
**Version Alignment**: `Engine v2.8.0` | `Model v1.0.0-HGB` | `Policy v1.2.0`  

---

## 1. Synchronous Response Contract (`POST /v1/risk/evaluate`)

This contract defines the immediate synchronous JSON response returned to the payment gateway within the 35ms SLA.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RiskSentinelDecisionResponse",
  "type": "object",
  "required": [
    "transaction_id",
    "evaluation_id",
    "timestamp_iso",
    "risk_score",
    "risk_band",
    "decision",
    "action",
    "reasons",
    "engine_metadata"
  ],
  "properties": {
    "transaction_id": { "type": "string", "format": "uuid" },
    "evaluation_id": { "type": "string", "format": "uuid" },
    "timestamp_iso": { "type": "string", "format": "date-time" },
    "risk_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "risk_band": { "type": "string", "enum": ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"] },
    "decision": { "type": "string", "enum": ["APPROVED", "CHALLENGED", "REVIEW_REQUIRED", "DECLINED"] },
    "action": { "type": "string", "enum": ["APPROVE", "STEP_UP_CHALLENGE", "MANUAL_REVIEW", "DECLINE"] },
    "reasons": {
      "type": "object",
      "properties": {
        "primary_code": { "type": "string" },
        "all_codes": { "type": "array", "items": { "type": "string" } },
        "narrative": { "type": "string" },
        "causal_evidence": { "type": "object" }
      }
    },
    "engine_metadata": {
      "type": "object",
      "properties": {
        "engine_version": { "type": "string" },
        "model_version": { "type": "string" },
        "model_type": { "type": "string", "enum": ["MODEL_B_STATEFUL_HGB", "MODEL_A_CAUSAL_BASELINE_FALLBACK"] },
        "feature_version": { "type": "string" },
        "policy_version": { "type": "string" },
        "operating_threshold": { "type": "number" },
        "fallback_triggered": { "type": "boolean" },
        "execution_latency_ms": { "type": "number" }
      }
    }
  }
}
```

---

## 2. Immutable Decision Audit Event Contract (Asynchronous Ledger)

Every evaluated transaction generates an immutable audit record dispatched asynchronously to the security audit store.

```json
{
  "event_id": "aud_9a82b1c4-5d6e-4f3a-b8c9-1e2f3a4b5c6d",
  "event_timestamp_utc": "2026-08-31T15:30:00.124Z",
  "transaction_id": "tx_41a87b32-9c10-4f8e-a22b-0e8317d6c342",
  "merchant_id": "mer_88301924",
  "lineage": {
    "engine_version": "v2.8.0-prod",
    "model_id": "model_b_stateful_hgb_v1.0.0",
    "model_artifact_hash": "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    "feature_pipeline_version": "v2.8.0-causal-21dim",
    "policy_rule_id": "pol_rule_transfer_high_risk_decline",
    "operating_threshold_applied": 0.990
  },
  "runtime_telemetry": {
    "execution_latency_ms": 6.84,
    "state_store_latency_ms": 2.11,
    "inference_latency_ms": 3.42,
    "fallback_mode_active": false,
    "state_lookup_status": "CACHE_HIT"
  },
  "input_snapshot_masked": {
    "step": 412,
    "type": "TRANSFER",
    "amount": 284100.50,
    "sender_masked": "C192***410",
    "sender_old_balance": 284100.50,
    "dest_masked": "C841***902",
    "dest_old_balance": 0.00
  },
  "causal_features_extracted": {
    "diff_orig_bal_amt": 0.00,
    "ratio_orig_bal_amt": 0.999996,
    "is_orig_zero": 0,
    "is_dest_zero": 1,
    "orig_prev_tx_cnt": 0,
    "dest_prev_in_tx_cnt": 3,
    "dest_unique_orig_cnt": 3,
    "is_sender_cold_start": 1,
    "is_dest_cold_start": 0
  },
  "evaluation_result": {
    "raw_model_score": 0.998412,
    "risk_band": "HIGH_RISK",
    "decision": "DECLINED",
    "action_enforced": "DECLINE",
    "primary_reason_code": "RC_EXACT_BALANCE_DRAIN",
    "reason_codes": [
      "RC_EXACT_BALANCE_DRAIN",
      "RC_HIGH_RISK_CHANNEL_COMBO",
      "RC_NEW_ACCOUNT_LARGE_OUTFLOW"
    ]
  },
  "integrity_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 3. Privacy, Masking & Regulatory Defense

1. **PII and Account Masking**: In non-audit analytics exports, customer IDs (`nameOrig`, `nameDest`) are cryptographically salted and masked (`C192***410`) to satisfy GDPR and PCI-DSS requirements.
2. **Reproducibility Guarantee**: The audit record stores the exact model artifact SHA256 hash and raw feature vector. Any risk decision can be deterministically re-evaluated offline to yield identical results during forensic inquiries.
3. **Immutability**: Audit logs are written to append-only storage with tamper-evident cryptographic chaining.
