# Risk Sentinel — P1.1 Implementation Gap Audit v2
**Document ID**: `AUDIT-P1.1-GAP-002`  
**Date**: `2026-09-02`  
**Phase**: `Phase P1.1 — Decision Economics & False-Positive Cost Simulator`  
**Track Alignment**: `Razorpay AI Buildathon — Track 02: AI Risk Manager`  
**Audit Scope**: `Read-Only Pre-Implementation Feasibility, Boundary, & Architectural Audit`  
**Implementation Status**: **`IMPLEMENTATION NOT STARTED (AUDIT ONLY)`**  

---

## 1. Executive Summary

This audit establishes the pre-implementation baseline for **Phase P1.1: Decision Economics + False-Positive Cost Simulator**.

In high-throughput payment risk management, selecting a classification threshold is not an abstract mathematical exercise; it is an operational and economic trade-off. Lowering the threshold captures more fraud but inflates false-positive operational friction (merchant interventions, 2FA drop-off, customer friction). Raising the threshold reduces merchant friction but exposes the gateway to catastrophic balance-drain fraud.

**Current Baseline Status**:
- The project already has a rudimentary static cost calculator in `BenchmarksPage.tsx` that computes cost for a single fixed threshold ($\theta^* = 0.990$) using an $\alpha$ slider.
- The project possesses rich empirical research artifacts generated during Phase 2.7 (`threshold_sensitivity.csv`, `cost_audit.json`, `policy_analysis.json`).
- However, the current system **lacks a dynamic, multi-threshold economic exploration service**, lacks backend analytics API endpoints, and currently hardcodes single-point values in the client.

**Core Architectural Safety Guarantee**:
- Phase P1.1 must be built as a strictly **read-only analytical service**.
- The simulator will explore hypothetical operational trade-offs across thresholds ($\theta \in [0.90, 0.999]$) and friction multipliers ($\alpha \in [0.1\%, 5.0\%]$).
- It will **NEVER mutate or override the frozen production policy** ($\theta^* = 0.990, \theta_{\text{med}} = 0.900$) and will not affect real-time inference or webhook processing.

---

## 2. Current Project State Snapshot

```
==================================================================================================
PROPERTY                        RECORDED VALUE / SYSTEM STATE
==================================================================================================
Repository Root                 C:\Users\raahe\Downloads\razorpay
Version Control State           Standalone Project Directory (non-git initialized root)
Engine Version                  v2.8.0-prod (API v2.9.0)
Champion ML Model               Model B (36-dim Stateful HistGradientBoostingClassifier)
Fallback ML Model               Model A (15-dim Causal Baseline HistGradientBoostingClassifier)
Operating Production Threshold  θ* = 0.990 (High Risk Decline), θ_med = 0.900 (Medium Risk Review)
Razorpay Test Mode Status       Phase P0 Verified (POST /v1/webhooks/razorpay operational)
Frontend Architecture           React 18 + TypeScript + Vite v6.4.3 (Google Stitch Design System)
Active Backend Test Suite       37/37 Tests Passing in tests/run_all_tests.py
==================================================================================================
```

---

## 3. Detailed Artifact Inspection

We inspected the five primary Phase 2.7 research artifacts located in `research/phase2_7/artifacts/`:

### A. `research/phase2_7/artifacts/threshold_sensitivity.csv`
- **File Dimensions**: 15 rows × 18 columns.
- **Data Split Evaluated**: **STRICTLY VALIDATION DATA** (PaySim steps 336–377, 973,173 transactions, 570 true fraud cases).
- **Thresholds Represented**: Dense ladder of 15 operating thresholds:
  `[0.900, 0.910, 0.920, 0.930, 0.940, 0.950, 0.960, 0.970, 0.975, 0.980, 0.985, 0.990, 0.995, 0.997, 0.999]`.
- **Columns Available**:
  `threshold`, `tp`, `fp`, `tn`, `fn`, `precision`, `recall`, `f1`, `fpr`, `fnr`,
  `detected_fraud_amount`, `missed_fraud_amount`, `flagged_nonfraud_amount`,
  `total_cost_fp_0.1%`, `total_cost_fp_0.5%`, `total_cost_fp_1.0%`, `total_cost_fp_2.0%`, `total_cost_fp_5.0%`.
- **Key Empirical Observations**:
  - Across $\theta \in [0.900, 0.990]$, recall remains $1.0000$ ($570/570$ frauds detected, $\$0$ missed fraud dollars).
  - False positives drop monotonically from $123$ ($\theta=0.90$) down to $119$ ($\theta=0.990$).
  - At $\theta = 0.995$, the first fraud is missed ($fn=1$, missed amount $\$6,391.60$).
  - At $\theta = 0.999$, all frauds are missed ($fn=570$, missed amount $\$769,750,597.32$).
- **API Safety**: Safe and structured for read-only analytical serialization.

### B. `research/phase2_7/artifacts/cost_audit.json`
- **Core Formula**: $\text{Total Cost} = \text{FN Missed Fraud Dollars} + \alpha \times \text{FP Flagged Legitimate Volume}$
- **Dimensional Consistency**: Confirmed mathematically consistent:
  $$\text{Currency} + [\text{Dimensionless} \times \text{Currency}] = \text{Currency}$$
- **Disjointness Audit**: Disjoint partition confirmed ($FN \cap FP = \emptyset$).
- **Alpha Sensitivity Range**:
  - $0.1\%$: Minimal operational friction / automated challenge with near-zero drop-off.
  - $0.5\%$: Low operational friction / frictionless step-up (e.g. fast push notification/biometric).
  - $1.0\%$: Standard industry baseline / manual review queue + minor customer drop-off.
  - $2.0\%$: Elevated friction / substantial drop-off and support contacts.
  - $5.0\%$: Severe friction / high false decline business impact and merchant churn.
- **Mandatory Disclosure**: Explicitly documents that $\alpha$ factors represent exploratory sensitivity modeling and must NOT be represented as Razorpay's actual internal unit economics.

### C. `research/phase2_7/artifacts/policy_analysis.json`
- **Two Distinct Evaluations**:
  1. `validation_policy_evaluation` (steps 336–377): 973,173 transactions; 570 frauds; 119 FPs at $\theta \ge 0.99$.
  2. `future_test_policy_evaluation` (steps 378–743): 955,744 transactions; 3,996 frauds detected; 14 missed ($399k missed vs $6.32B protected); 154 FPs at $\theta \ge 0.99$.
- **Bypass Channel Tier**: Confirms PAYMENT, CASH_IN, and DEBIT channels have 0 fraud and pass via fast-track approval without friction.

### D. `research/phase2_7/artifacts/score_distribution.json` & `phase2_7_results.json`
- Contains percentile distribution forensics and training isolation verification proving zero future lookahead.

---

## 4. Backend Inspection

We examined `src/engine/api.py`, `src/engine/schemas.py`, `src/engine/decision_engine.py`, `src/engine/policy_engine.py`, and `src/engine/model_manager.py`:

```
==================================================================================================
AUDIT QUESTION                                                    INSPECTION FINDING
==================================================================================================
A. Does a threshold-sensitivity API already exist?               NO. Zero /v1/analytics endpoints exist.
B. Does a cost-analysis API already exist?                       NO. Cost calculations are not exposed via API.
C. Does any endpoint expose benchmark artifacts?                 NO. Only /v1/model/info exposes model manifest.
D. Is there an existing safe pattern for read-only analytics?     YES. Decoupled helper/service pattern (similar to
                                                                 audit_logger.get_events and model_manager.manifest).
E. Would P1.1 require changing a frozen production file?         NO. A new read-only module can be added.
F. Can P1.1 be a separate service without touching decision core? YES. src/engine/analytics/economics_service.py
G. Are there existing API contracts that should be reused?       YES. Response envelope conventions and Pydantic schemas.
==================================================================================================
```

---

## 5. Frontend Inspection

We inspected `frontend/src/pages/BenchmarksPage.tsx`, `DashboardPage.tsx`, `StreamPage.tsx`, `client.ts`, and `engine.ts`:

- **Current Implementation in `BenchmarksPage.tsx`**:
  - Contains an interactive $\alpha$ slider ($0.1\% - 5.0\%$).
  - However, it hardcodes only a **single point** from the future test set ($\theta = 0.990$: $fnDollars = \$399,045.08$, $fpVolume = \$9,216,222.88$).
  - It does **NOT allow exploring other thresholds** ($\theta \in [0.90, 0.999]$).
  - It does **NOT display the cost curve** or trade-off curve across thresholds.
- **Reusability & Placement**:
  - `BenchmarksPage.tsx` is the ideal host for the expanded **Decision Economics & False-Positive Cost Simulator**.
  - Reusable components: `BenchmarkMetricCard.tsx`, `DataSourceBadge.tsx`, existing Tailwind styling.
  - Adding this capability to `BenchmarksPage.tsx` does NOT touch or alter real-time transaction processing (`StreamPage.tsx`), the live decision engine, or webhook handling.

---

## 6. Frozen File Integrity Audit

We computed SHA-256 hashes of all 9 frozen components and compared them against the verified Phase 2.14 baseline:

```
======================================================================================================================
PROTECTED COMPONENT              EXPECTED SHA-256 HASH                             ACTUAL HASH MATCH? STATUS
======================================================================================================================
model_b_stateful_hgb.joblib      5ea5926344e12215fe6e9fe91b593a99feb581747c...     MATCH (100%)       UNTOUCHED & FROZEN
model_a_causal_hgb.joblib        ea356eb3bd713de47c1cdc34389db461a02c95e8c...     MATCH (100%)       UNTOUCHED & FROZEN
policy_engine.py                 b61ab343af0e5aa84726db1d96700b89b8e22b88a...     MATCH (100%)       UNTOUCHED & FROZEN
decision_engine.py               1b5f1615f90548fa5eba94231e207d43d3e0bf7a6...     MATCH (100%)       UNTOUCHED & FROZEN
feature_pipeline.py              41b315ed0eaff96321d7dfabab72f5fdd1a254a39...     MATCH (100%)       UNTOUCHED & FROZEN
model_manager.py                 e2400085415e93554e480d8ff4f78fe22852c007f...     MATCH (100%)       UNTOUCHED & FROZEN
schemas.py                       de16b6bba9d2b235611adf52272ff033cb40eafff...     MATCH (100%)       UNTOUCHED & FROZEN
audit_logger.py                  044951b6a014a07cd48179cd9d5388373ddd2b4e0...     MATCH (100%)       UNTOUCHED & FROZEN
state_store.py                   f7f6615a0277bb11631fe4dbc0be5ddde26a1c288...     MATCH (100%)       UNTOUCHED & FROZEN
======================================================================================================================
```
**Verdict**: All 9 files remain 100% byte-for-byte identical to baseline.

---

## 7. Validation vs Test Boundary Audit

Maintaining rigorous data boundaries is essential to prevent data leakage and cherry-picking:

```
==================================================================================================
BOUNDARY PRINCIPLE               EVALUATION EVIDENCE & METHODOLOGY
==================================================================================================
1. Threshold Selection Split     VALIDATION SPLIT (PaySim Steps 336–377, 973,173 transactions).
                                 The operating threshold θ* = 0.990 was selected based strictly on
                                 validation cost minimization and zero false negatives on validation.

2. Out-of-Sample Test Split      FUTURE HELD-OUT TEST (PaySim Steps 378–743, 955,744 transactions).
                                 Evaluated strictly once with fixed θ* = 0.990. Produces 96.29% precision,
                                 99.65% recall, $6.32B protected, and $399k missed.

3. Zero Test-Set Tuning          The simulator must NOT tune or re-optimize thresholds on future test data.
                                 Multi-threshold curves shown in the simulator must explicitly cite whether
                                 they represent the Validation Dense Ladder or the Frozen Test Point.

4. Decoupled Sensitivity Scope   Friction multiplier α ∈ [0.1%, 5.0%] is an exploratory scenario tool
                                 for risk managers, not an empirical Razorpay merchant loss figure.
==================================================================================================
```

---

## 8. Economic Model Audit

### Mathematical Consistency
$$\text{Total Loss}(\theta, \alpha) = \text{FN Dollars}(\theta) + \alpha \times \text{FP Flagged Volume}(\theta)$$

- **Dimension**: $[\text{USD}] + [\text{Dimensionless} \times \text{USD}] = [\text{USD}]$.
- **Disjoint Sets**: Fraudulent transactions ($y=1$) and legitimate transactions ($y=0$) are mutually exclusive. Therefore, no transaction can simultaneously contribute to $\text{FN Dollars}$ and $\text{FP Flagged Volume}$.
- **Monotonicity Dynamics**:
  - As $\theta \to 1.0$: $\text{FP Volume} \to 0$ (friction drops to 0), but $\text{FN Dollars} \to \text{Total Fraud Dollars}$ (disastrous fraud loss).
  - As $\theta \to 0.0$: $\text{FN Dollars} \to 0$, but $\text{FP Volume} \to \text{Total Non-Fraud Volume}$ (prohibitive customer friction).
  - **Global Minimum**: Located at $\theta^* = 0.990$ across all reasonable $\alpha \in [0.1\%, 5.0\%]$.

---

## 9. Missing Capabilities (Genuinely Needed for P1.1)

1. **Backend Analytics Endpoint**:
   - Need `GET /v1/analytics/threshold-sensitivity`: Serves the dense 15-point threshold sensitivity matrix from `threshold_sensitivity.csv`.
   - Need `GET /v1/analytics/cost-simulation?alpha=0.01`: Computes or retrieves projected system cost across the threshold ladder for any requested $\alpha \in [0.001, 0.05]$.
2. **Frontend Sensitivity Controls**:
   - Dual-slider / selector interface allowing analysts to change $\theta \in [0.90, 0.999]$ AND $\alpha \in [0.1\%, 5.0\%]$.
   - Comparative tabular display showing: Precision, Recall, Missed Fraud Dollars, Flagged Non-Fraud Volume, and Net Economic Loss.
   - Prominent indicator showing the **Frozen Production Operating Point ($\theta^* = 0.990$)**.
3. **Institutional Disclaimers**:
   - Clear banner stating: *"Analytical sensitivity exploration only — does not alter frozen production policy or Razorpay unit economics."*

---

## 10. File-by-File Implementation Plan

```
==================================================================================================
FILE PATH                                        CLASSIFICATION      RESPONSIBILITY & SAFETY
==================================================================================================
src/engine/analytics/economics_service.py        [B. MAY ADD]        Read-only service that loads Phase 2.7
                                                                     artifacts and computes cost scenarios.
                                                                     Zero mutation of production inference.

src/engine/api.py                                [A. MUST MODIFY]    Mount GET /v1/analytics/threshold-sensitivity
                                                                     and GET /v1/analytics/cost-simulation.

frontend/src/api/client.ts                       [A. MUST MODIFY]    Add getThresholdSensitivity() and
                                                                     getCostSimulation(alpha).

frontend/src/types/engine.ts                     [A. MUST MODIFY]    Add TypeScript interfaces for
                                                                     ThresholdSensitivityRecord & CostSimulationResult.

frontend/src/pages/BenchmarksPage.tsx            [A. MUST MODIFY]    Expand the sensitivity simulator section
                                                                     with multi-threshold exploration & comparison.

tests/test_economics_analytics.py                [B. MAY ADD]        Automated test suite verifying data
                                                                     integrity, cost equations, and immutability.

src/engine/decision_engine.py                    [C. MUST NOT MODIFY] Core inference pipeline (FROZEN).
src/engine/policy_engine.py                      [C. MUST NOT MODIFY] Core policy thresholds (FROZEN).
src/engine/model_manager.py                      [C. MUST NOT MODIFY] Model loader & hashes (FROZEN).
src/engine/feature_pipeline.py                   [C. MUST NOT MODIFY] Causal feature extractors (FROZEN).
src/engine/audit_logger.py                       [C. MUST NOT MODIFY] Cryptographic audit logger (FROZEN).
src/engine/state_store.py                        [C. MUST NOT MODIFY] State store & circuit breaker (FROZEN).
src/engine/schemas.py                            [C. MUST NOT MODIFY] Core evaluation schemas (FROZEN).
src/engine/artifacts/*.joblib                    [C. MUST NOT MODIFY] Model binary weights (FROZEN).
research/phase2_7/artifacts/*                    [D. READ-ONLY]      Source research artifacts (READ-ONLY).
==================================================================================================
```

---

## 11. Proposed API Contract

### Endpoint 1: `GET /v1/analytics/threshold-sensitivity`
- **Query Parameters**: None.
- **Response**: Array of 15 threshold points:
  ```json
  [
    {
      "threshold": 0.990,
      "tp": 570,
      "fp": 119,
      "tn": 972484,
      "fn": 0,
      "precision": 0.827286,
      "recall": 1.000000,
      "f1": 0.905481,
      "detected_fraud_amount": 769750597.32,
      "missed_fraud_amount": 0.0,
      "flagged_nonfraud_amount": 6434547.49,
      "is_production_threshold": true,
      "split": "VALIDATION_SPLIT_STEPS_336_377"
    }
  ]
  ```

### Endpoint 2: `GET /v1/analytics/cost-simulation?alpha=0.01`
- **Query Parameters**: `alpha` (float, $0.0001 \le \alpha \le 0.1000$, default: $0.01$).
- **Response**:
  ```json
  {
    "alpha": 0.01,
    "alpha_percentage": "1.0%",
    "cost_equation": "Total_Cost = Missed_Fraud_FN_Dollars + alpha * Flagged_Legitimate_Volume",
    "disclaimer": "Exploratory scenario sensitivity modeling. Does NOT represent actual Razorpay unit economics.",
    "production_operating_point": {
      "threshold": 0.990,
      "missed_fraud_amount": 0.0,
      "flagged_nonfraud_amount": 6434547.49,
      "total_projected_loss": 64345.47,
      "is_global_minimum": true
    },
    "simulation_table": [ ... ]
  }
  ```

---

## 12. Proposed Frontend Contract

- **Location**: `BenchmarksPage.tsx` under a new tab or dedicated section: **"Interactive Decision Economics & Trade-off Explorer"**.
- **Interactive Controls**:
  1. $\alpha$ slider ($0.1\% - 5.0\%$).
  2. Operating threshold selector ($\theta \in [0.900, 0.999]$).
  3. Toggle: **Validation Dense Ladder (15 points)** vs **Future Test Verified Point ($\theta^* = 0.990$)**.
- **Visuals**:
  - Comparison table highlighting the cost curve minimum at $\theta = 0.990$.
  - Badges clearly separating `BENCHMARK RESEARCH` from `ANALYTICAL SENSITIVITY`.
  - Prominent banner: *"Analytical sensitivity exploration only — does not alter frozen production policy ($\theta^* = 0.990$) or Razorpay unit economics."*

---

## 13. Test Plan for Phase P1.1

1. **Artifact Loading & Integrity**: Verify `threshold_sensitivity.csv` and `cost_audit.json` load cleanly.
2. **Schema & Range Validation**: Verify `alpha` is bounded ($0.0001 \le \alpha \le 0.10$) and rejects negative/astronomical values.
3. **Equation Exactness**: Verify $\text{Total Cost} = \text{FN} + \alpha \times \text{FP}$ matches to floating-point precision.
4. **Disjointness Audit**: Assert $FN \cap FP = \emptyset$.
5. **Frozen Policy Invariance**: Run `engine.evaluate()` before and after analytics API calls and assert identical scores and decisions.
6. **Core Hash Check**: Assert all 9 core file SHA-256 hashes remain 100% identical.
7. **Frontend Build & Render**: Verify `npm run build` succeeds with zero TypeScript errors.

---

## 14. Risk Register

```
==================================================================================================
RISK DESCRIPTION                                                  SEVERITY   MITIGATION STRATEGY
==================================================================================================
1. Accidental test-set threshold tuning                           HIGH       Explicitly label that the multi-threshold
                                                                             ladder is from Validation data (steps 336–377).

2. Misrepresenting exploratory alpha as Razorpay economics        HIGH       Display permanent disclaimer on API and UI:
                                                                             "Scenario sensitivity — not Razorpay economics."

3. Mutating production policy from UI slider                      CRITICAL   Backend API is 100% read-only GET requests;
                                                                             zero state or policy mutation methods exist.

4. Client-side financial calculation discrepancies                MEDIUM     Server-side computation with deterministic
                                                                             unit tests; frontend only renders verified results.

5. Regression in frozen model weights or hashes                   CRITICAL   SHA-256 boot guard & CI assertion on all 9 files.
==================================================================================================
```

---

## 15. Exact STOP/GO Recommendation

### **AUDIT VERDICT: GO (PROCEED TO IMPLEMENTATION ONLY UPON USER APPROVAL)**

- **Safety**: Fully safe to implement. P1.1 requires **ZERO changes to the frozen decision engine, models, thresholds, or webhooks**.
- **Architecture**: A cleanly decoupled `src/engine/analytics/` service with read-only GET endpoints preserves 100% system integrity.
- **Files to touch**:
  - New: `src/engine/analytics/economics_service.py`, `tests/test_economics_analytics.py`
  - Modified: `src/engine/api.py` (mount 2 read-only GET routes), `frontend/src/api/client.ts`, `frontend/src/types/engine.ts`, `frontend/src/pages/BenchmarksPage.tsx`.

---

### FINAL STOP CONDITION SATISFIED

**P1.1 Implementation Gap Audit v2 COMPLETE — IMPLEMENTATION NOT STARTED.**

I have stopped as instructed. Awaiting your explicit direction to proceed with implementation!
