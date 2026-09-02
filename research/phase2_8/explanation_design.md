# Risk Sentinel Explanation Engine — Architectural Specification
**Document ID**: `EXP-ENG-2.8-001`  
**Status**: `FROZEN DESIGN`  
**Target Execution SLA**: $\le 1.0\text{ ms}$ CPU Attribution  

---

## 1. Objective & Explanation Paradigm

A critical requirement of Risk Sentinel is providing **verifiable, causal, and defensible explanations** for every decision. When an auditor or judge asks:

> *"Why did Risk Sentinel flag transaction `TX-89211` as High Risk?"*

The system must return deterministic, non-hallucinatory evidence directly grounded in the transaction's causal features.

---

## 2. Evaluation of Explainability Approaches

| Method | Latency ($p99$) | Causal Grounding | Production Feasibility | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Pure Post-Hoc SHAP** | $45 - 120\text{ ms}$ | Moderate (Correlation-based background) | Unacceptable for $<35\text{ms}$ gateway SLA | **REJECTED (Latency blocker)** |
| **Permutation Importance** | $>500\text{ ms}$ | Dataset-level only | Impossible at real-time inference | **REJECTED (Batch only)** |
| **Pure Rule-Based Heuristics**| $<0.2\text{ ms}$ | High | Detached from ML non-linear interactions | **REJECTED (ML Disconnect)** |
| **Hybrid Causal Attribution** | **$0.3 - 0.8\text{ ms}$** | **Extremely High (Causal feature tree bounds)** | **Production-Ready, Deterministic, Zero Jitter**| **SELECTED (CHAMPION)** |

---

## 3. The Hybrid Causal Attribution Architecture

The engine combines **Tree Path Contribution (Logit Delta Attribution)** with **Deterministic Causal Semantic Encoders**:

```
[Inference Tree Split Attributions] ──┐
                                     ├──> [Causal Reason Resolver] ──> [Structured Reason Codes + Narrative]
[Point-in-Time & Historical Deltas] ──┘
```

### Attribution Workflow:
1. **Feature Attribution Vector**: For transaction $t$, compute normalized feature contribution $c_i = w_i \cdot (x_i - \bar{x}_i)$.
2. **Top-K Driver Selection**: Select top 3 positive contributors pushing the score into `HIGH_RISK` or `MEDIUM_RISK`.
3. **Semantic Reason Code Mapping**: Map dominant contributors to certified **Reason Codes** with exact numeric contextual evidence.

---

## 4. Certified Reason Code Catalog

| Reason Code | Trigger Criteria | Severity | Analyst Narrative Template |
| :--- | :--- | :--- | :--- |
| **`RC_EXACT_BALANCE_DRAIN`** | $\text{oldbalanceOrg} == \text{amount}$ and $\text{amount} > 0$ | **CRITICAL** | "Transaction attempts exact 100% liquidation of available sender balance (Amount: \${amount:,.2f} == Balance: \${oldbalanceOrg:,.2f})." |
| **`RC_SEVERE_LIQUIDITY_DRAIN`**| $\frac{\text{amount}}{\text{oldbalanceOrg} + 1} > 0.90$ | **HIGH** | "Transaction drains {drain_pct:.1f}% of sender total account liquidity." |
| **`RC_DEST_MULE_VELOCITY`** | $\text{dest\_prev\_in\_tx\_cnt} \ge 5$ and $\text{dest\_unique\_orig\_cnt} \ge 3$ | **HIGH** | "Destination account exhibits mule aggregation pattern ({dest_unique_orig_cnt} unique senders within {dest_prev_in_tx_cnt} prior transactions)." |
| **`RC_NEW_ACCOUNT_LARGE_OUTFLOW`**| $\text{is\_sender\_cold\_start} == 1$ and $\text{amount} > \$100,000$ | **MEDIUM** | "First observed transaction for sender initiating high-value outflow (\${amount:,.2f})." |
| **`RC_HIGH_RISK_CHANNEL_COMBO`**| $\text{type} \in [\text{'TRANSFER'}, \text{'CASH\_OUT'}]$ and $\text{dest\_is\_zero} == 1$ | **MEDIUM** | "Outflow routed to destination with uninitialized/zero initial balance via high-risk transfer channel." |
| **`RC_SENDER_AMOUNT_DEVIATION`**| $\text{orig\_amt\_vs\_avg\_ratio} > 5.0$ and $\text{orig\_prev\_tx\_cnt} > 0$ | **MEDIUM** | "Transaction amount is {ratio:.1f}x higher than sender historical average (\${avg:,.2f})." |
| **`RC_BENIGN_BASELINE`** | $S < 0.90$ across low-risk profile | **LOW** | "Normal transaction velocity, adequate balance headroom, and established channel baseline." |

---

## 5. Output Explanation Schema

```json
{
  "primary_reason_code": "RC_EXACT_BALANCE_DRAIN",
  "reason_codes": [
    "RC_EXACT_BALANCE_DRAIN",
    "RC_HIGH_RISK_CHANNEL_COMBO"
  ],
  "narrative": "Transaction attempts exact 100% liquidation of available sender balance ($181,954.34) via high-risk TRANSFER channel.",
  "causal_evidence": {
    "sender_old_balance": 181954.34,
    "transaction_amount": 181954.34,
    "liquidity_headroom_after_tx": 0.00,
    "liquidation_percentage": 100.0,
    "channel": "TRANSFER",
    "destination_previous_incoming_txs": 0,
    "sender_historical_tx_count": 0
  }
}
```
