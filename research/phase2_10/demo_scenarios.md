# Risk Sentinel — Master Demo Scenarios & Fixture Guide
**Document ID**: `DEMO-SCENARIO-2.10-001`  
**Status**: `FROZEN DEMO SPECIFICATION`  
**Target Environment**: Live Competition Demo & Judge Viva  

---

## Complete Catalog of 9 Master Demo Scenarios

These 9 reproducible scenario fixtures showcase Risk Sentinel's core capabilities, causal integrity, real-time explanations, fallback resilience, and cryptographic auditability.

---

### Scenario 1: Normal Everyday Consumer Payment (`DEMO-01`)
- **Objective**: Demonstrate zero-friction instant authorization on benign traffic.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-001-normal",
    "step": 450,
    "type": "PAYMENT",
    "amount": 84.50,
    "nameOrig": "C_ALICE_01",
    "oldbalanceOrg": 1200.00,
    "nameDest": "M_BOOKSTORE_01",
    "oldbalanceDest": 0.00
  }
  ```
- **Expected Decision**: **`APPROVED`** | **Action**: `APPROVE`
- **Expected Risk Band**: `LOW_RISK` | **Risk Score**: `0.001790`
- **Expected Reason**: `RC_BENIGN_BASELINE` ("Normal transaction velocity, adequate balance headroom, and established channel baseline.")
- **Execution Path**: Fast-track empirical bypass / low-risk scoring ($<2\text{ms}$ latency).

---

### Scenario 2: Suspicious Severe Liquidity Outflow (`DEMO-02`)
- **Objective**: Demonstrate intelligent step-up friction on high-value borderline risk.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-002-suspicious",
    "step": 451,
    "type": "TRANSFER",
    "amount": 9500.00,
    "nameOrig": "C_BOB_02",
    "oldbalanceOrg": 10000.00,
    "nameDest": "C_NEW_DEST_02",
    "oldbalanceDest": 500.00
  }
  ```
- **Expected Decision**: **`CHALLENGED`** | **Action**: `STEP_UP_CHALLENGE`
- **Expected Risk Band**: `MEDIUM_RISK` ($0.90 \le S < 0.99$)
- **Expected Reason**: `RC_SEVERE_LIQUIDITY_DRAIN` ("Transaction drains 95.0% of sender total account liquidity ($9,500.00 of $10,000.00).")
- **Execution Path**: Scored high-risk channel $\to$ dynamic 2FA / Biometric prompt.

---

### Scenario 3: Critical Fraud — Exact 100% Balance Liquidation (`DEMO-03`)
- **Objective**: Demonstrate high-precision automated decline on full balance drain attacks.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-003-critical",
    "step": 452,
    "type": "TRANSFER",
    "amount": 284100.50,
    "nameOrig": "C_VICTIM_03",
    "oldbalanceOrg": 284100.50,
    "nameDest": "C_MULE_03",
    "oldbalanceDest": 0.00
  }
  ```
- **Expected Decision**: **`DECLINED`** | **Action**: `DECLINE`
- **Expected Risk Band**: `HIGH_RISK` | **Risk Score**: `0.998412` ($S \ge 0.99$)
- **Expected Reason**: `RC_EXACT_BALANCE_DRAIN` ("Transaction attempts exact 100% liquidation of available sender balance ($284,100.50) via high-risk TRANSFER channel.")
- **Execution Path**: Model B GBDT $\to$ High-Risk Intercept $\to$ Intercepts $100\%$ fraud dollars.

---

### Scenario 4: Benign Cold-Start Account (`DEMO-04`)
- **Objective**: Prove that brand new accounts without history are **not** falsely flagged as fraud.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-004-coldstart",
    "step": 453,
    "type": "TRANSFER",
    "amount": 50.00,
    "nameOrig": "C_FRESH_USER_04",
    "oldbalanceOrg": 1000.00,
    "nameDest": "C_DEST_04",
    "oldbalanceDest": 200.00
  }
  ```
- **Expected Decision**: **`APPROVED`** | **Action**: `APPROVE`
- **Expected Risk Band**: `LOW_RISK` | **Risk Score**: `0.001790`
- **Context Verified**: `is_sender_cold_start = 1`, `is_dest_cold_start = 0`.
- **Viva Defense**: Proves FROZEN Rule #010 compliance (Cold-start is context, not fraud evidence).

---

### Scenario 5: State Store Outage / Timeout & Circuit Breaker Recovery (`DEMO-05`)
- **Objective**: Prove zero-downtime resilience via automatic **Model A (Causal Baseline)** fallback.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-005-fallback",
    "step": 454,
    "type": "TRANSFER",
    "amount": 190000.00,
    "nameOrig": "C_FALLBACK_USER_05",
    "oldbalanceOrg": 190000.00,
    "nameDest": "C_FALLBACK_DEST_05",
    "oldbalanceDest": 0.00
  }
  ```
- **Simulated Trigger**: State store latency $>15\text{ms}$ or Redis connection dropped.
- **Expected Response**:
  - `model_type`: `"MODEL_A_CAUSAL_BASELINE_FALLBACK"`
  - `fallback_triggered`: `true`
  - `decision`: **`DECLINED`** (Model A accurately flags the point-in-time drain without cache access).
  - `reasons`: Includes `"RC_FALLBACK_EVALUATION_ACTIVE"`.

---

### Scenario 6: Cryptographic Model Tamper Defense (`DEMO-06`)
- **Objective**: Prove defensive security against corrupted or modified model binaries.
- **Trigger**: Altering 1 byte in `model_a_causal_hgb.joblib` or `model_b_stateful_hgb.joblib`.
- **Expected System Action**: `ModelManager` verifies SHA-256 against `engine_manifest.json` on startup. The engine refuses to boot and raises `ModelIntegrityError: Model SHA-256 mismatch!`.

---

### Scenario 7: Full Causal Explanation & Evidence Inspection (`DEMO-07`)
- **Objective**: Showcase regulatory-compliant, deterministic explanation metadata for analysts.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-007-explanation",
    "step": 456,
    "type": "CASH_OUT",
    "amount": 99000.00,
    "nameOrig": "C_DRAIN_07",
    "oldbalanceOrg": 100000.00,
    "nameDest": "C_DEST_07",
    "oldbalanceDest": 500.00
  }
  ```
- **Expected Output Explanations**:
  ```json
  {
    "primary_code": "RC_SEVERE_LIQUIDITY_DRAIN",
    "all_codes": ["RC_SEVERE_LIQUIDITY_DRAIN", "RC_NEW_ACCOUNT_LARGE_OUTFLOW"],
    "narrative": "Transaction drains 99.0% of sender total account liquidity ($99,000.00 of $100,000.00).",
    "causal_evidence": {
      "amount": 99000.00,
      "oldbalanceOrg": 100000.00,
      "liquidation_pct": 99.0,
      "channel": "CASH_OUT",
      "is_sender_cold_start": 1
    }
  }
  ```

---

### Scenario 8: Immutable Audit Trail & Cryptographic Chaining (`DEMO-08`)
- **Objective**: Prove anti-tamper compliance via SHA-256 block hash chaining and PII masking.
- **Input Payload**:
  ```json
  {
    "transaction_id": "demo-tx-008-audit",
    "step": 457,
    "type": "TRANSFER",
    "amount": 120.00,
    "nameOrig": "C192837465",
    "oldbalanceOrg": 2000.00,
    "nameDest": "C987654321",
    "oldbalanceDest": 100.00
  }
  ```
- **Audit Verification**:
  - `sender_masked`: `"C192***465"`
  - `dest_masked`: `"C987***321"`
  - `integrity_hash`: `sha256(previous_event_hash + current_event_json)` $\implies$ Mathematical immutability.

---

### Scenario 9: Financial Cost & Threshold Tradeoff (`DEMO-09`)
- **Objective**: Showcase why operating threshold $\theta^* = 0.99$ was chosen over naive $\theta = 0.50$.
- **Validation Comparison**:
  - At $\theta = 0.50$: FPR $= 0.68\%$, Precision $= 7.91\%$, 6,644 false positives $\implies$ **Total Financial Loss = \$12,968,269.83**.
  - At $\theta = 0.99$: FPR $= 0.012\%$, Precision $= 82.73\%$, 119 false positives $\implies$ **Total Financial Loss = \$64,345.47 (Global Minimum)**.
- **Future Test Intercept**: Intercepts **\$6,323,408,725.18** out of \$6,323,807,770.26 (**99.9937% of fraud dollars**).
