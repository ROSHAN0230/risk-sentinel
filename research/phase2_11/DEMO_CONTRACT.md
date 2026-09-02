# Risk Sentinel — Master Demo Scenarios & UI Fixture Contract
**Document ID**: `DEMO-CTR-2.11-001`  
**Status**: `FROZEN DEMO CONTRACT`  
**Target Interactive Interface**: Google Stitch Demo Console  

---

## The 9 Frozen Demo Fixtures (`DEMO-01` through `DEMO-09`)

```
┌─────────┬───────────────────────────────┬────────────┬──────────────────┬─────────────────────────────┐
│ ID      │ Scenario Name                 │ Expected   │ Action           │ Primary Reason Code         │
├─────────┼───────────────────────────────┼────────────┼──────────────────┼─────────────────────────────┤
│ DEMO-01 │ Normal Consumer Payment       │ APPROVED   │ APPROVE          │ RC_BENIGN_BASELINE          │
│ DEMO-02 │ Suspicious Liquidity Outflow  │ CHALLENGED │ STEP_UP_CHALLENGE│ RC_SEVERE_LIQUIDITY_DRAIN   │
│ DEMO-03 │ Critical 100% Balance Drain   │ DECLINED   │ DECLINE          │ RC_EXACT_BALANCE_DRAIN      │
│ DEMO-04 │ Benign Cold-Start Account     │ APPROVED   │ APPROVE          │ RC_BENIGN_BASELINE          │
│ DEMO-05 │ State Outage Fallback Mode    │ DECLINED   │ DECLINE          │ RC_EXACT_BALANCE_DRAIN      │
│ DEMO-06 │ Model Tamper Defense          │ BOOT_ERROR │ SYSTEM_HALT      │ N/A (ModelIntegrityError)   │
│ DEMO-07 │ Causal Explanation Inspection │ DECLINED   │ DECLINE          │ RC_SEVERE_LIQUIDITY_DRAIN   │
│ DEMO-08 │ Cryptographic Audit Ledger    │ APPROVED   │ APPROVE          │ RC_BENIGN_BASELINE          │
│ DEMO-09 │ Financial Cost Tradeoff       │ BENCHMARK  │ THRESHOLD_SWEEP  │ N/A (Validation Analysis)   │
└─────────┴───────────────────────────────┴────────────┴──────────────────┴─────────────────────────────┘
```

---

### Fixture `DEMO-01`: Normal Everyday Consumer Payment
- **Payload**: `{"transaction_id": "demo-01", "step": 450, "type": "PAYMENT", "amount": 84.50, "nameOrig": "C_ALICE_01", "oldbalanceOrg": 1200.00, "nameDest": "M_BOOKSTORE_01", "oldbalanceDest": 0.00}`
- **Expected Decision**: `APPROVED` | **Action**: `APPROVE` | **Band**: `LOW_RISK` | **Score**: `0.001790`
- **Fallback Involved**: `false` | **Audit Behavior**: Chained event logged with masked ID `C_AL***_01`.
- **Audience Takeaway**: Proves that legitimate low-risk commerce is fast-tracked with sub-2ms latency.

---

### Fixture 2. `DEMO-02`: Suspicious Severe Liquidity Outflow
* **Goal**: Demonstrate decoupled Medium-Risk policy tier on high-value borderline risk.
* **Input**:
  ```json
  {
    "transaction_id": "tx-demo-02",
    "step": 324,
    "type": "TRANSFER",
    "amount": 976662.30,
    "nameOrig": "C1959219454",
    "oldbalanceOrg": 982857.46,
    "nameDest": "C2061756973",
    "oldbalanceDest": 2453029.29
  }
  ```
* **Expected Result**:
  * **Operating Score**: `0.9830` (Medium Risk in $[0.9000, 0.9900)$)
  * **Risk Band**: `MEDIUM_RISK`
  * **Decision**: `REVIEW_REQUIRED`
  * **Action**: `MANUAL_REVIEW` (amount $\ge \$50,000$)
  * **Primary Reason**: `RC_SEVERE_LIQUIDITY_DRAIN` (99.37% balance drain)
* **Judge/Viva Takeaway**: Demonstrates that medium-risk transactions do not get declined blindly; they are routed to the decoupled manual review / challenge queue.")
- **Fallback Involved**: `false` | **Audit Behavior**: Step-up event logged.
- **Audience Takeaway**: Demonstrates risk-to-action decoupling (applying dynamic 2FA challenge on borderline risk instead of a disruptive hard decline).

---

### Fixture `DEMO-03`: Critical Fraud — Exact 100% Balance Liquidation
- **Payload**: `{"transaction_id": "demo-03", "step": 452, "type": "TRANSFER", "amount": 284100.50, "nameOrig": "C_VICTIM_03", "oldbalanceOrg": 284100.50, "nameDest": "C_MULE_03", "oldbalanceDest": 0.00}`
- **Expected Decision**: `DECLINED` | **Action**: `DECLINE` | **Band**: `HIGH_RISK` | **Score**: `0.998412`
- **Primary Reason**: `RC_EXACT_BALANCE_DRAIN` ("Transaction attempts exact 100% liquidation of available sender balance ($284,100.50) via high-risk TRANSFER channel.")
- **Fallback Involved**: `false` | **Audit Behavior**: High-risk decline event logged.
- **Audience Takeaway**: Proves high-precision automated defense intercepting full balance-drain attacks without human delay.

---

### Fixture `DEMO-04`: Benign Cold-Start Account (Context vs Fraud)
- **Payload**: `{"transaction_id": "demo-04", "step": 453, "type": "TRANSFER", "amount": 50.00, "nameOrig": "C_FRESH_USER_04", "oldbalanceOrg": 1000.00, "nameDest": "C_DEST_04", "oldbalanceDest": 200.00}`
- **Expected Decision**: `APPROVED` | **Action**: `APPROVE` | **Band**: `LOW_RISK` | **Score**: `0.001790`
- **Fallback Involved**: `false` | **Context**: `is_sender_cold_start = 1`.
- **Audience Takeaway**: Proves adherence to FROZEN #010 (Cold-start is contextual metadata, not automatic evidence of fraud).

---

### Fixture `DEMO-05`: State Store Outage / Timeout (Model A Fallback)
- **Payload**: `{"transaction_id": "demo-05", "step": 454, "type": "TRANSFER", "amount": 190000.00, "nameOrig": "C_FALLBACK_05", "oldbalanceOrg": 190000.00, "nameDest": "C_FALLBACK_D_05", "oldbalanceDest": 0.00}`
- **Simulated Condition**: State store timeout $>15\text{ms}$ or Redis connection down.
- **Expected Output**: `model_type = "MODEL_A_CAUSAL_BASELINE_FALLBACK"`, `fallback_triggered = true`, `decision = DECLINED`.
- **Audience Takeaway**: Demonstrates zero-downtime resilience; Model A provides uninterrupted, highly accurate defense even during database outages.

---

### Fixture `DEMO-06`: Cryptographic Model Tamper Defense
- **Action**: Startup integrity check on model binaries.
- **Outcome**: Engine verifies SHA-256 against `engine_manifest.json`. Modifying 1 byte triggers `ModelIntegrityError` and halts boot.
- **Audience Takeaway**: Proves defense against supply-chain attacks and corrupted model deployments.

---

### Fixture `DEMO-07`: Full Causal Explanation & Evidence Inspection
- **Payload**: `{"transaction_id": "demo-07", "step": 456, "type": "CASH_OUT", "amount": 99000.00, "nameOrig": "C_DRAIN_07", "oldbalanceOrg": 10000.00, "nameDest": "C_DEST_07", "oldbalanceDest": 500.00}`
- **Expected Output**: Structured Reason Codes + `causal_evidence` dictionary showing exact amount, balance, liquidation percentage, and channel.
- **Audience Takeaway**: Demonstrates transparent, verifiable decision lineage for compliance officers and viva judges.

---

### Fixture `DEMO-08`: Cryptographically Chained Audit Ledger
- **Payload**: `{"transaction_id": "demo-08", "step": 457, "type": "TRANSFER", "amount": 120.00, "nameOrig": "C192837465", "oldbalanceOrg": 2000.00, "nameDest": "C987654321", "oldbalanceDest": 100.00}`
- **Expected Output**: Audit event with masked IDs (`C192***465`), SHA-256 model hash, and chained block hash.
- **Audience Takeaway**: Proves anti-repudiation and regulatory compliance.

---

### Fixture `DEMO-09`: Financial Cost & Threshold Tradeoff
- **Analysis Screen**: Validation threshold sweep comparing $\theta = 0.50$ (\$12.97M loss) vs $\theta = 0.99$ (\$64,345 loss).
- **Audience Takeaway**: Shows how cost-sensitive threshold optimization saves millions in false-positive customer friction.
