# Risk Sentinel — UI Data Boundary & Contract Specification
**Document ID**: `UI-DAT-2.11-001`  
**Status**: `FROZEN UI DATA CONTRACT`  

---

## 1. Data Classification Tiers

The frontend dashboard is strictly partitioned into 5 distinct data categories:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TIER A: Live Decision Data (Real-time evaluation stream)              │
│  - Fields: transaction_id, risk_score, risk_band, decision, action,   │
│            primary_code, narrative, causal_evidence, latency_ms        │
│  - Source: POST /v1/risk/evaluate                                      │
├────────────────────────────────────────────────────────────────────────┤
│ TIER B: Historical Benchmark Metrics (Frozen Academic Research)        │
│  - Fields: PR-AUC (0.9850), Precision (96.29%), Recall (99.65%),       │
│            FPR (0.0162%), Fraud Dollars Detected ($6.32B / 99.99%)     │
│  - Source: Future Test Evaluation (Steps 378–743 on PaySim)            │
├────────────────────────────────────────────────────────────────────────┤
│ TIER C: Demo-Only Illustrative Values (Interactive Simulations)        │
│  - Fixtures: DEMO-01 to DEMO-09 (Normal, Suspicious, Drain, Fallback)  │
│  - Source: Pre-built fixture catalog for judge evaluation              │
├────────────────────────────────────────────────────────────────────────┤
│ TIER D: Research Forensics & Lineage (Audit Evidence)                  │
│  - Fields: Training Step Range (1–322), Model SHA-256 Checksums,       │
│            Validation Split Cost Minimization Curves                   │
├────────────────────────────────────────────────────────────────────────┤
│ TIER E: Required Production & Methodology Disclaimers                  │
│  - Disclaimers on: 0.990 threshold, PaySim channels, alpha multiplier │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Permitted UI Visualizations per Tier

### Tier A: Live Decision Panel
- **Score Meter**: Radial or linear progress bar ($0.000$ to $1.000$) with colored segments:
  - Green: `[0.000, 0.900)`
  - Yellow: `[0.900, 0.990)`
  - Red: `[0.990, 1.000]`
- **Action Badge**: Tag displaying `APPROVED`, `STEP_UP_CHALLENGE`, `MANUAL_REVIEW`, or `DECLINED`.
- **Reason Card**: Primary reason title, plain-English summary, and evidence key-value grid.
- **Engine Status Pill**: `MODEL_B_STATEFUL_HGB` (Green) or `FALLBACK_MODEL_A` (Blue/Amber) + execution latency.

### Tier B: Benchmark Metrics Dashboard
- **PR-AUC**: `0.9850` (Model B) vs `0.9843` (Model A Baseline)
- **Precision**: `96.29%` (3,996 True Positives / 154 False Positives)
- **Recall**: `99.65%` (3,996 / 4,010 Fraud Transactions Intercepted)
- **Dollars Protected**: `\$6,323,408,725.18` out of `\$6,323,807,770.26` ($99.9937\%$)
- **False Positive Rate**: `0.0162%` ($16$ per $100,000$ legitimate transactions)

---

## 3. UI Display Prohibitions (What NOT to Render)

1. **DO NOT render** "99% Probability of Fraud" (Must label as "Operating Risk Score: 0.990").
2. **DO NOT render** post-transaction balance fields (`newbalanceOrig`, `newbalanceDest`).
3. **DO NOT render** unmasked customer account numbers (Must mask as `C192***465`).
4. **DO NOT render** claims of real-world Razorpay proprietary financial loss without scenario disclaimer tags.
