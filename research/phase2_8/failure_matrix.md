# Risk Sentinel Failure & Edge Case Matrix
**Document ID**: `FAIL-MTX-2.8-001`  
**Status**: `FROZEN SPECIFICATION`  

---

## Complete Failure, Exception & Edge Case Matrix

| # | Failure Mode / Edge Case | Trigger Condition | System Risk | Expected Engine Behavior | Safe Response Action | Logging & Telemetry |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Malformed JSON Payload** | Unparseable body or invalid JSON syntax | Ingestion crash | Fast-reject at API gateway boundary | HTTP 400 `MALFORMED_JSON` | Error log + Ingestion counter |
| **2** | **Missing Mandatory Field** | Payload missing `amount`, `type`, or balances | Model vector misalignment | Pydantic schema validation failure | HTTP 422 `MISSING_FIELD` | Validation error log |
| **3** | **Negative Transaction Amount**| `amount < 0.0` | Inverted logic / balance corruption | Reject at schema layer | HTTP 422 `INVALID_AMOUNT` | Security alert for probe |
| **4** | **Zero Transaction Amount** | `amount == 0.0` | Division by zero in ratios | Reject at schema layer | HTTP 422 `ZERO_AMOUNT_NOT_PERMITTED` | Telemetry counter |
| **5** | **Unknown Transaction Type** | `type` not in `[TRANSFER, CASH_OUT, PAYMENT, CASH_IN, DEBIT]` | Feature one-hot vector corruption | Schema validation rejection | HTTP 422 `UNKNOWN_CHANNEL` | Schema error log |
| **6** | **Unseen Sender (Cold Start)**| `nameOrig` not present in state store | Erroneous assumption of fraud | Initialize sender counters to 0; set `is_sender_cold_start = 1` | Normal ML scoring with cold-start context | Track cold-start metric |
| **7** | **Unseen Destination** | `nameDest` not present in state store | Erroneous assumption of fraud | Initialize dest counters to 0; set `is_dest_cold_start = 1` | Normal ML scoring with cold-start context | Track cold-start metric |
| **8** | **State Store Unreachable** | Redis/In-Memory state store connection error | Complete pipeline stall | **Graceful Fallback Mode**: Route to **Model A (Causal Baseline)** | Seamless scoring with Model A; Decision unaffected | `ALERT_STATE_STORE_DOWN` + Audit flag |
| **9** | **State Store Lookup Timeout**| Read latency exceeds $15.0\text{ ms}$ | SLA breach ($>35\text{ms}$) | **Immediate Circuit Breaker**: Abort lookup, switch to **Model A** | Seamless scoring with Model A; Decision unaffected | `WARN_STATE_TIMEOUT` + Audit flag |
| **10**| **Model B Inference Exception**| Unexpected memory/numeric failure in GBDT | Pipeline 500 error | **Graceful Degradation**: Route directly to **Model A** | Score with Model A; Return decision | `ERROR_MODEL_B_CRASH` + Sentry event |
| **11**| **NaN / Inf in Feature Vector**| Extreme balance or calculation overflow | Corrupt model evaluation | Replace with certified neutral imputation ($0.0$ / median) | Continue scoring; Flag feature anomaly in reasons | `WARN_NUMERIC_IMPUTATION` |
| **12**| **Duplicate Transaction ID** | Identical `transaction_id` submitted $\le 5\text{ mins}$ | Double billing / replay attack | **Idempotency Check**: Return cached original decision without re-scoring or re-incrementing state | Return original cached response | `LOG_IDEMPOTENT_REPLAY` |
| **13**| **Extreme Transaction Amount** | $\text{amount} > \$100,000,000.00$ | Numeric overflow / severe liquidity exposure | Normal feature computation with log transform | Scored normally $\to$ triggers `HIGH_RISK` + `DECLINE` | `HIGH_VALUE_TRANSACTION_LOG` |
| **14**| **Hard Gateway Timeout** | Total request latency exceeds $35.0\text{ ms}$ | Gateway timeout error | **Configurable Fail-Safe Rule**: If merchant policy allows, return `STEP_UP_CHALLENGE` / `MANUAL_REVIEW` | Return safe fallback challenge | `CRITICAL_GATEWAY_TIMEOUT` |
| **15**| **Model Version Mismatch** | Request header requests deprecated model | Invalid feature mapping | Reject request or redirect to active champion | HTTP 400 `INVALID_MODEL_VERSION` | Version mismatch log |
| **16**| **Async Audit Ledger Failure** | Audit buffer full or disk write error | Loss of regulatory record | Non-blocking in-memory queue spill to disk backup | Transaction response completes normally | `CRITICAL_AUDIT_WRITE_FAILURE` |
