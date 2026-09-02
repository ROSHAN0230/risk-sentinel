# Risk Sentinel Decision Engine — Architectural Specification
**Document ID**: `ARCH-ENG-2.8-001`  
**Status**: `FROZEN DESIGN`  
**Target Execution Environment**: Real-Time Low-Latency Payment Risk Gateway  

---

## 1. Executive Overview & Pipeline Architecture

The Risk Sentinel Decision Engine is a real-time, causally strict, explainable risk management pipeline. It ingests in-flight transaction events, extracts causal point-in-time and historical stateful features, scores risk using an audited HistGradientBoosting classifier, applies a configurable decision policy, generates deterministic human-readable explanations, and emits an immutable audit event.

### End-to-End Transaction Lifecycle (10 Stages)

```
[In-Flight Payment Request]
            │
            ▼
[Stage 1: Input Validation & Schema Sanitization]
            │  (Reject malformed payloads, NaN/null, negative amounts)
            ▼
[Stage 2: Stateful Context Read (Pre-Decision)]
            │  (Fetch historical state strictly < t; trigger fallback if >15ms)
            ▼
[Stage 3: Causal Feature Assembly]
            │  (Compute Model B 21-dim or Model A 15-dim feature vector)
            ▼
[Stage 4: Model Inference Execution]
            │  (HistGradientBoosting raw logit & probability evaluation)
            ▼
[Stage 5: Risk Score & Band Resolution]
            │  (Generate continuous score [0.0, 1.0] and risk band: LOW / MED / HIGH)
            ▼
[Stage 6: Causal Explanation & Reason Generation]
            │  (Extract deterministic causal drivers and human-readable narrative)
            ▼
[Stage 7: Policy & Action Resolution Engine]
            │  (Decouple Risk from Action: APPROVE / STEP_UP / REVIEW / DECLINE)
            ▼
[Stage 8: Stateful Entity Update (Post-Decision)]
            │  (Increment sender, dest, interaction counters strictly AFTER decision)
            ▼
[Stage 9: Immutable Audit Event Dispatch]
            │  (Asynchronously write full decision lineage to secure audit ledger)
            ▼
[Stage 10: Synchronous Decision Response]
               (Return structured response contract to payment gateway in <35ms)
```

---

## 2. Detailed Pipeline Stages

### Stage 1: Input Validation & Schema Sanitization
- **Purpose**: Ensure structural and data integrity before downstream compute.
- **Contract**:
  - `transaction_id`: UUIDv4 string (Required).
  - `timestamp_step`: Integer $\ge 1$ (Current discrete simulation hour or ISO8601 epoch).
  - `type`: Enum `['TRANSFER', 'CASH_OUT', 'PAYMENT', 'CASH_IN', 'DEBIT']`.
  - `amount`: Float $> 0.0$ (Strictly positive, finite, non-NaN).
  - `sender_id`: String (Normalized, non-empty).
  - `sender_old_balance`: Float $\ge 0.0$ (Point-in-time balance prior to execution).
  - `dest_id`: String (Normalized, non-empty).
  - `dest_old_balance`: Float $\ge 0.0$ (Point-in-time balance prior to execution).
- **Failure Action**: Immediate HTTP 400 with `INVALID_SCHEMA` error code; zero model compute.

### Stage 2: Stateful Context Read (Pre-Decision)
- **Causal Guarantee**: Read historical state for `sender_id`, `dest_id`, and `(sender_id, dest_id)` interaction recorded **strictly prior to transaction $t$**.
- **State Read**:
  - `sender_state`: `{tx_count, cum_amount, max_amount, last_step, transfer_count, cash_out_count, unique_dest_set}`
  - `dest_state`: `{incoming_tx_count, incoming_cum_amount, incoming_max_amount, last_step, unique_sender_set}`
  - `interaction_state`: `{pair_tx_count, pair_last_step}`
- **Latency Guard & Timeout**: State lookup deadline is **15ms**. If cache lookup fails or exceeds deadline, the engine sets `fallback_mode = True` and proceeds immediately to Model A without dropping or blocking the transaction.

### Stage 3: Causal Feature Assembly
- **Zero Leakage Invariant**:
  - Features are computed using only Stage 1 inputs and Stage 2 pre-decision state.
  - Prohibited fields (`newbalanceOrig`, `newbalanceDest`, `isFlaggedFraud`, post-transaction deltas) are physically absent from the feature builder.
- **Feature Vectors**:
  - **Model B Vector (21 dimensions)**: Includes point-in-time liquidity ratios (`diff_orig_bal_amt`, `ratio_orig_bal_amt`), time indicators, sender velocity/deviations, destination aggregation counters, and cold-start indicators.
  - **Model A Vector (15 dimensions)**: Point-in-time inputs only (fallback path).

### Stage 4: Model Inference Execution
- **Runtime Engine**: Fast in-memory Scikit-Learn tree inference using pre-loaded frozen `HistGradientBoostingClassifier` binaries.
- **Execution Target**: $< 5\text{ms}$ CPU inference time per transaction.
- **Output**: Raw risk score $S \in [0.0, 1.0]$.

### Stage 5: Risk Score & Band Resolution
- **Semantics**: $S$ represents an **operating risk score** derived from balanced loss optimization, where higher values indicate severe balance drain and transfer-velocity anomalies.
- **Risk Bands**:
  - **`LOW_RISK`**: $S < 0.90$
  - **`MEDIUM_RISK`**: $0.90 \le S < 0.99$
  - **`HIGH_RISK`**: $S \ge 0.99$

### Stage 6: Causal Explanation & Reason Generation
- **Architecture**: Deterministic Causal Rule-Attribution Engine.
- **Operation**: Translates dominant feature deviations into standardized **Reason Codes** (e.g., `RC_EXACT_BALANCE_LIQUIDATION`, `RC_HIGH_VALUE_FIRST_TX`, `RC_DESTINATION_MULE_SURGE`) and generates an analyst-ready narrative.

### Stage 7: Policy & Action Resolution Engine
- **Decoupled Architecture**: Maps `{Risk Band, Reason Codes, Merchant Tier, Amount}` $\to$ `{Action}`.
- **Default Action Mapping**:
  - `LOW_RISK` $\to$ **`APPROVE`** (Zero friction, instant pass-through).
  - `MEDIUM_RISK` $\to$ **`STEP_UP_CHALLENGE`** (Trigger frictionless 2FA / Biometric / OTP).
  - `HIGH_RISK` $\to$ **`DECLINE`** (or High-Friction Step-Up / Manual Review per merchant configuration).

### Stage 8: Stateful Entity Update (Post-Decision)
- **Strict Sequencing**: State update occurs **exclusively after** Stage 7 decision generation.
- **Atomic Operations**:
  - Increment sender transaction counter, cumulative amount, rolling max, and add destination to sender destination set.
  - Increment destination incoming counter, cumulative incoming amount, and add sender to destination sender set.
  - Record interaction timestamp.

### Stage 9: Immutable Audit Event Dispatch
- **Async Execution**: Emits complete decision context to non-blocking audit buffer (Zero impact on p99 transaction latency).
- **Lineage Integrity**: Includes model version, feature hash, policy version, raw features, score, band, action, reason codes, and execution latency.

### Stage 10: Synchronous Decision Response
- **Response Format**: Strict JSON contract returned to caller within the **35ms SLA budget**.

---

## 3. Real-Time Latency Budget Breakdown

| Pipeline Stage | Target Latency (p50) | Target Latency (p99) | Timeout / SLA |
| :--- | :--- | :--- | :--- |
| **1. Validation & Parsing** | 0.2 ms | 0.8 ms | 2.0 ms |
| **2. Stateful Context Read** | 2.0 ms | 8.0 ms | **15.0 ms** (Triggers fallback) |
| **3. Causal Feature Assembly** | 0.5 ms | 1.5 ms | 3.0 ms |
| **4. Model Inference (GBDT)** | 1.5 ms | 4.5 ms | 10.0 ms |
| **5. Explanation Generation** | 0.3 ms | 1.0 ms | 2.0 ms |
| **6. Policy & Decision Mapping** | 0.1 ms | 0.4 ms | 1.0 ms |
| **7. Response Serialization** | 0.2 ms | 0.8 ms | 2.0 ms |
| **Total Synchronous Budget** | **4.8 ms** | **17.0 ms** | **35.0 ms** |
| *8. Async State & Audit Write* | *1.0 ms (Async)* | *5.0 ms (Async)* | *Non-blocking* |
