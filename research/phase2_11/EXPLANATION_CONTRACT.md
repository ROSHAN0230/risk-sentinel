# Risk Sentinel — Causal Explanation & Reason Contract
**Document ID**: `EXP-CTR-2.11-001`  
**Status**: `FROZEN EXPLANATION CONTRACT`  
**Resolver Engine**: `Hybrid Causal Attribution Engine` (`src/engine/explanation_resolver.py`)  

---

## 1. Explanation Integrity Boundaries

The frontend dashboard and analyst console must strictly adhere to the following explainability contracts:
1. **Deterministic & Evidence-Backed**: Every explanation narrative must be derived from verified Reason Codes and accompanied by the `causal_evidence` dictionary.
2. **Zero Hallucination / Zero Correlation Leakage**: Explanations must never cite unverified correlations, LLM-generated conjectures, or external demographic data.
3. **Zero Post-Transaction Balance Exposure**: Explanations must never reference post-transaction account balances (`newbalanceOrig`, `newbalanceDest`).

---

## 2. Certified Reason Code Catalog for UI Display

```
┌────────────────────────────────────────────────────────────────────────┐
│ CRITICAL SEVERITY REASON CODES                                         │
├──────────────────────────────┬─────────────────────────────────────────┤
│ RC_EXACT_BALANCE_DRAIN       │ 100% liquidation of sender balance.     │
│ RC_SEVERE_LIQUIDITY_DRAIN    │ Outflow drains >90% of available funds. │
├──────────────────────────────┼─────────────────────────────────────────┤
│ HIGH SEVERITY REASON CODES                                             │
├──────────────────────────────┬─────────────────────────────────────────┤
│ RC_DEST_MULE_VELOCITY        │ Recipient exhibits mule aggregation.    │
│ RC_HIGH_RISK_CHANNEL_COMBO   │ High-risk transfer to zero-balance dest.│
├──────────────────────────────┼─────────────────────────────────────────┤
│ MEDIUM SEVERITY REASON CODES                                           │
├──────────────────────────────┬─────────────────────────────────────────┤
│ RC_NEW_ACCOUNT_LARGE_OUTFLOW │ First-time sender initiating >$100k out.│
│ RC_SENDER_AMOUNT_DEVIATION   │ Outflow is >5x sender historical mean.  │
│ RC_FALLBACK_EVALUATION_ACTIVE│ State store offline; baseline active.   │
├──────────────────────────────┼─────────────────────────────────────────┤
│ LOW / INFORMATIONAL REASON CODES                                       │
├──────────────────────────────┬─────────────────────────────────────────┤
│ RC_BENIGN_BASELINE           │ Normal velocity, headroom & baseline.   │
└──────────────────────────────┴─────────────────────────────────────────┘
```

---

## 3. Standardized Narrative Templates

| Reason Code | Narrative Template | UI Display Badge |
| :--- | :--- | :--- |
| **`RC_EXACT_BALANCE_DRAIN`** | `"Transaction attempts exact 100% liquidation of available sender balance (${amount:,.2f}) via high-risk {channel} channel."` | `CRITICAL: 100% Balance Liquidation` (Red) |
| **`RC_SEVERE_LIQUIDITY_DRAIN`**| `"Transaction drains {drain_pct:.1f}% of sender total account liquidity (${amount:,.2f} of ${oldbalanceOrg:,.2f})."` | `HIGH: Severe Liquidity Drain` (Orange) |
| **`RC_DEST_MULE_VELOCITY`** | `"Destination account exhibits mule aggregation velocity ({dest_unique_orig_cnt} unique senders across {dest_prev_in_tx_cnt} prior transactions)."` | `HIGH: Mule Velocity Detected` (Orange) |
| **`RC_NEW_ACCOUNT_LARGE_OUTFLOW`**| `"First observed transaction for sender initiating high-value outflow (${amount:,.2f})."` | `MEDIUM: High-Value First Outflow` (Yellow) |
| **`RC_HIGH_RISK_CHANNEL_COMBO`**| `"Outflow routed to uninitialized/zero-balance destination via high-risk {channel} channel."` | `MEDIUM: High-Risk Channel Route` (Yellow) |
| **`RC_SENDER_AMOUNT_DEVIATION`**| `"Transaction amount is {ratio:.1f}x higher than sender historical average (${avg:,.2f})."` | `MEDIUM: Historical Volume Surge` (Yellow) |
| **`RC_FALLBACK_EVALUATION_ACTIVE`**| `"State store unavailable; decision derived from causal point-in-time baseline features."` | `INFO: Fallback Engine Active` (Blue) |
| **`RC_BENIGN_BASELINE`** | `"Normal transaction velocity, adequate balance headroom, and established channel baseline."` | `BENIGN: Normal Activity` (Green) |

---

## 4. UI Explanation Card Layout Contract

The UI explanation component must render:
1. **Primary Reason Badge**: Colored severity tag with `primary_code`.
2. **Plain-English Summary**: Formatted narrative string from template.
3. **Causal Evidence Grid**:
   - `Amount`: Formatted currency string (\${amount:,.2f})
   - `Sender Balance Prior`: Formatted currency string (\${oldbalanceOrg:,.2f})
   - `Liquidity Drain %`: Percentage badge ({liquidation_pct:.1f}%)
   - `Channel Route`: High-risk (`TRANSFER`/`CASH_OUT`) vs Fast-path badge
   - `Sender History Depth`: Number of prior transactions
   - `Destination History Depth`: Number of prior incoming transactions
