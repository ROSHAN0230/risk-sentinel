# Risk Sentinel — Policy & Decision Resolution Contract
**Document ID**: `POL-CTR-2.11-001`  
**Status**: `FROZEN POLICY CONTRACT`  
**Policy Engine Version**: `v1.2.0-frozen`  

---

## 1. Locked Decision Thresholds & Risk Bands

```
[Risk Score: S ∈ [0.0, 1.0]]
        │
        ├── S < 0.9000                ──> LOW_RISK
        ├── 0.9000 ≤ S < 0.9900       ──> MEDIUM_RISK
        └── S ≥ 0.9900                ──> HIGH_RISK
```

### Exact Boundary Behavior (Audited in Phase 2.10 Audit 1):
- `0.8999` $\to$ **`LOW_RISK`** $\to$ **`APPROVE`**
- `0.9000` $\to$ **`MEDIUM_RISK`** $\to$ **`STEP_UP_CHALLENGE`** / **`MANUAL_REVIEW`**
- `0.9001` $\to$ **`MEDIUM_RISK`** $\to$ **`STEP_UP_CHALLENGE`** / **`MANUAL_REVIEW`**
- `0.9899` $\to$ **`MEDIUM_RISK`** $\to$ **`STEP_UP_CHALLENGE`** / **`MANUAL_REVIEW`**
- `0.9900` $\to$ **`HIGH_RISK`** $\to$ **`DECLINE`**
- `0.9901` $\to$ **`HIGH_RISK`** $\to$ **`DECLINE`**

---

## 2. Mathematical Calibration Semantics

> [!WARNING]
> **Strict Semantic Boundary**:
> The risk score $S = 0.9900$ is **NOT** a statement that "there is a 99% probability of fraud."  
> Because the underlying GBDT model was trained with `class_weight='balanced'` on data with an empirical fraud rate of $0.0819\%$ ($1$ in $1,220$ transactions), the training loss shifted the baseline prior log-odds by $\ln(1219.4) \approx +7.106$.  
> 
> A raw model score of $S = 0.9900$ translates to a true calibrated Bayesian posterior risk of:
> $$P_{\text{true}}(\text{Fraud}) = \sigma\left(\ln\left(\frac{0.99}{0.01}\right) - 7.106\right) = \sigma(4.595 - 7.106) = \sigma(-2.511) \approx \mathbf{7.51\%}$$
> $\theta^* = 0.9900$ was selected exclusively on Validation Split data because it achieved the **global minimum operational financial loss (\$64,345.47)** while intercepting $100.00\%$ of fraud volume on validation data.

---

## 3. Decoupled Action Resolution Matrix

| Channel Type | Risk Band | Amount Threshold | Decision Enum | Action Enum | User / Gateway Experience |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PAYMENT`, `CASH_IN`, `DEBIT` | *Any* | *Any* | **`APPROVED`** | **`APPROVE`** | Instant authorization via fast-track empirical bypass. |
| `TRANSFER`, `CASH_OUT` | **`LOW_RISK`** ($S < 0.90$) | *Any* | **`APPROVED`** | **`APPROVE`** | Instant frictionless approval ($99.98\%$ of legitimate traffic). |
| `TRANSFER`, `CASH_OUT` | **`MEDIUM_RISK`** ($0.90 \le S < 0.99$) | $< \$50,000$ | **`CHALLENGED`** | **`STEP_UP_CHALLENGE`** | Triggers interactive 2FA / SMS OTP / Biometric challenge. |
| `TRANSFER`, `CASH_OUT` | **`MEDIUM_RISK`** ($0.90 \le S < 0.99$) | $\ge \$50,000$ | **`REVIEW_REQUIRED`**| **`MANUAL_REVIEW`** | Held in analyst investigation queue (SLA: 15 mins). |
| `TRANSFER`, `CASH_OUT` | **`HIGH_RISK`** ($S \ge 0.99$) | *Any* | **`DECLINED`** | **`DECLINE`** | Immediate hard stop (intercepts $99.99\%$ of fraud dollars). |

---

## 4. Channel Bypass Classification

- **Empirical Classification**: The automatic approval on `PAYMENT`, `CASH_IN`, and `DEBIT` is an **empirical observation on the PaySim benchmark dataset** (where $0$ fraud occurred across 3,592,211 records).
- **Production Truth Boundary**: In live commercial deployments, the engine architecture supports ML scoring across all transaction types. The bypass must not be represented as a universal fraud axiom.
