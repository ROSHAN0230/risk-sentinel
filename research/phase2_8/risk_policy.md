# Risk Sentinel Operating Policy & Action Resolution Specification
**Document ID**: `POLICY-2.8-001`  
**Status**: `FROZEN POLICY SPECIFICATION`  
**Policy Engine Version**: `v1.2.0-frozen`  

---

## 1. Separation of Risk from Action (Core Architectural Principle)

A foundational flaw in naive ML systems is hardcoding model thresholds directly to binary outcomes (`if prob > 0.5: decline()`). Risk Sentinel enforces a strict **two-layer decoupling**:

```
[Model Inference] ──> [Risk Score: S ∈ [0.0, 1.0]]
                             │
                             ▼
[Risk Classification] ──> [Risk Band: LOW / MEDIUM / HIGH]
                             │
                             ▼
[Policy Engine]   ──> [Contextual Action: APPROVE / STEP_UP / REVIEW / DECLINE]
                        (Configured by merchant rules, transaction value & risk appetite)
```

### Why Decoupling is Essential:
1. **Dynamic Risk Appetite**: A luxury merchant may tolerate higher friction (e.g. 2FA on medium-risk) to eliminate chargebacks, while an instant digital micro-payment merchant requires zero-friction approvals for transactions under \$5.
2. **Zero-Downtime Policy Tuning**: Risk operations teams can alter action rules (e.g. shifting `MEDIUM_RISK` from manual review to automated biometric challenge during traffic surges) without retraining or redeploying the underlying ML models.
3. **Graceful Regulatory Step-Up**: Accommodates Strong Customer Authentication (SCA / 3D-Secure 2.0) mandates by routing borderline risk directly to dynamic cryptographic challenges rather than hard declines.

---

## 2. Risk Bands & Mathematical Thresholds

The underlying model uses `class_weight='balanced'` GBDT loss. As mathematically proven in Phase 2.7 Audit 2, the decision boundaries are calibrated as follows:

| Risk Band | Model Score Range ($S$) | Empirical Posterior Risk | Validation F1 / Recall | Recommended Primary Action |
| :--- | :--- | :--- | :--- | :--- |
| **`LOW_RISK`** | $0.000 \le S < 0.900$ | $< 0.05\%$ (Negligible) | Recall: $100\%$, FPR: $0.00\%$ | **`APPROVE`** |
| **`MEDIUM_RISK`** | $0.900 \le S < 0.990$ | $0.05\% \le P < 7.5\%$ (Elevated) | Recall: $100\%$, Prec: $82.5\%$ | **`STEP_UP_CHALLENGE`** / **`MANUAL_REVIEW`** |
| **`HIGH_RISK`** | $0.990 \le S \le 1.000$ | $\ge 7.5\%$ (Critical) | Recall: $99.65\%$, Prec: $96.29\%$ | **`DECLINE`** (or **`HARD_STEP_UP`**) |

---

## 3. Action Resolution Rules & Policy Matrix

### Action Catalog

| Action Code | Execution Type | User / System Experience | Target Use Case |
| :--- | :--- | :--- | :--- |
| **`APPROVE`** | Synchronous Fast Path | Transaction authorized immediately without user prompt. | Low risk scores across all channels. |
| **`STEP_UP_CHALLENGE`**| Synchronous Interactive| Invokes frictionless 2FA (SMS OTP, In-app push, Biometric prompt). | Borderline risk ($0.90 \le S < 0.99$) or high amount first transfers. |
| **`MANUAL_REVIEW`** | Asynchronous Queue | Transaction held in analyst investigation queue (SLA: 15 mins). | High-value borderline transfers or repeated soft challenge failures. |
| **`DECLINE`** | Synchronous Hard Stop | Transaction rejected with clear, non-leaky reason code. | Extreme risk ($S \ge 0.99$), exact full drain, or blacklisted mule. |

### Configurable Resolution Matrix

```json
{
  "policy_version": "v1.2.0-frozen",
  "rules": [
    {
      "channel_filter": ["CASH_IN", "DEBIT", "PAYMENT"],
      "action": "APPROVE",
      "rationale": "Empirical low-risk channel bypass in PaySim benchmark"
    },
    {
      "channel_filter": ["TRANSFER", "CASH_OUT"],
      "conditions": {
        "risk_band": "LOW_RISK"
      },
      "action": "APPROVE"
    },
    {
      "channel_filter": ["TRANSFER", "CASH_OUT"],
      "conditions": {
        "risk_band": "MEDIUM_RISK",
        "amount_usd_lt": 10000.0
      },
      "action": "STEP_UP_CHALLENGE"
    },
    {
      "channel_filter": ["TRANSFER", "CASH_OUT"],
      "conditions": {
        "risk_band": "MEDIUM_RISK",
        "amount_usd_gte": 10000.0
      },
      "action": "MANUAL_REVIEW"
    },
    {
      "channel_filter": ["TRANSFER", "CASH_OUT"],
      "conditions": {
        "risk_band": "HIGH_RISK"
      },
      "action": "DECLINE"
    }
  ]
}
```

---

## 4. Channel Policy Refinement & Production Caveat

- **PaySim Benchmark Policy**: `CASH_IN`, `DEBIT`, and `PAYMENT` bypass ML scoring and receive automatic `APPROVE` decisions, as verified across 3,592,211 benchmark rows.
- **Production Defense Contract**: In live commercial deployments, the engine architecture **must support ML scoring across all transaction types**, treating the bypass as a configurable merchant rule rather than an immutable machine learning axiom.
