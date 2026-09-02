# Risk Sentinel — API Integration Contract
**Document ID**: `API-CTR-2.11-001`  
**Status**: `FROZEN CONTRACT`  
**Engine Compatibility**: `v2.9.0` | `FastAPI backend` (`src/engine/api.py`)  

---

## 1. REST Endpoint Overview

| Method | Endpoint | Description | SLA / Timeout |
| :--- | :--- | :--- | :--- |
| `POST` | `/v1/risk/evaluate` | Synchronously evaluates transaction risk and returns action + explanation. | 35.0 ms |
| `GET` | `/v1/health` | Returns service health, state store status, and model hash. | 5.0 ms |
| `GET` | `/v1/model/info` | Returns model manifest, training lineage, feature list, and frozen threshold. | 5.0 ms |
| `GET` | `/v1/audit/events` | Retrieves recent cryptographically chained audit events (supports `?limit=N`). | 20.0 ms |

---

## 2. Evaluation Request Schema (`POST /v1/risk/evaluate`)

### Request JSON Body Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvaluateRequest",
  "type": "object",
  "required": [
    "transaction_id",
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "nameDest",
    "oldbalanceDest"
  ],
  "properties": {
    "transaction_id": {
      "type": "string",
      "description": "Unique transaction UUID/ID string",
      "example": "tx-41a87b32-9c10-4f8e-a22b-0e8317d6c342"
    },
    "step": {
      "type": "integer",
      "minimum": 1,
      "description": "Discrete simulation hour or chronological epoch step (1 to 743+)",
      "example": 452
    },
    "type": {
      "type": "string",
      "enum": ["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"],
      "description": "Transaction channel type",
      "example": "TRANSFER"
    },
    "amount": {
      "type": "number",
      "exclusiveMinimum": 0.0,
      "description": "Transaction monetary amount in base currency units (must be > 0.0)",
      "example": 284100.50
    },
    "nameOrig": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128,
      "description": "Originating sender account identifier",
      "example": "C192837465"
    },
    "oldbalanceOrg": {
      "type": "number",
      "minimum": 0.0,
      "description": "Sender point-in-time balance immediately prior to transaction execution",
      "example": 284100.50
    },
    "nameDest": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128,
      "description": "Destination recipient account identifier",
      "example": "C987654321"
    },
    "oldbalanceDest": {
      "type": "number",
      "minimum": 0.0,
      "description": "Destination point-in-time balance immediately prior to transaction execution",
      "example": 0.00
    },
    "merchant_id": {
      "type": "string",
      "description": "Optional merchant or gateway account identifier",
      "default": "default_merchant",
      "example": "mer_88301924"
    }
  }
}
```

---

## 3. Evaluation Response Schema (`HTTP 200 OK`)

### Response JSON Body Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvaluateResponse",
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
    "transaction_id": { "type": "string" },
    "evaluation_id": { "type": "string" },
    "timestamp_iso": { "type": "string", "format": "date-time" },
    "risk_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Operating risk score (uncalibrated balanced GBDT score)"
    },
    "risk_band": {
      "type": "string",
      "enum": ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]
    },
    "decision": {
      "type": "string",
      "enum": ["APPROVED", "CHALLENGED", "REVIEW_REQUIRED", "DECLINED"]
    },
    "action": {
      "type": "string",
      "enum": ["APPROVE", "STEP_UP_CHALLENGE", "MANUAL_REVIEW", "DECLINE"]
    },
    "reasons": {
      "type": "object",
      "required": ["primary_code", "all_codes", "narrative", "causal_evidence"],
      "properties": {
        "primary_code": { "type": "string" },
        "all_codes": { "type": "array", "items": { "type": "string" } },
        "narrative": { "type": "string" },
        "causal_evidence": { "type": "object" }
      }
    },
    "engine_metadata": {
      "type": "object",
      "required": [
        "engine_version",
        "model_version",
        "model_type",
        "policy_version",
        "operating_threshold",
        "fallback_triggered",
        "execution_latency_ms"
      ],
      "properties": {
        "engine_version": { "type": "string", "example": "v2.8.0-prod" },
        "model_version": { "type": "string", "example": "v1.0.0-HGB" },
        "model_type": {
          "type": "string",
          "enum": ["MODEL_B_STATEFUL_HGB", "MODEL_A_CAUSAL_BASELINE_FALLBACK"]
        },
        "policy_version": { "type": "string", "example": "v1.2.0-frozen" },
        "operating_threshold": { "type": "number", "example": 0.990 },
        "fallback_triggered": { "type": "boolean", "example": false },
        "execution_latency_ms": { "type": "number", "example": 2.261 }
      }
    }
  }
}
```

---

## 4. Error Responses & HTTP Status Codes

| Status Code | Error Code | Trigger Condition | Response Body Format |
| :--- | :--- | :--- | :--- |
| `HTTP 400` | `MALFORMED_JSON` | Invalid JSON syntax in request body. | `{"error_code": "MALFORMED_JSON", "message": "..."}` |
| `HTTP 422` | `INVALID_SCHEMA` | Missing mandatory fields, negative amount, negative balance, or invalid channel Enum. | `{"error_code": "INVALID_SCHEMA", "message": "...", "details": [...]}` |
| `HTTP 500` | `INTERNAL_ENGINE_ERROR` | Unhandled backend exception (fail-safe circuit breaker prevents this in standard flows). | `{"error_code": "INTERNAL_ENGINE_ERROR", "message": "..."}` |
