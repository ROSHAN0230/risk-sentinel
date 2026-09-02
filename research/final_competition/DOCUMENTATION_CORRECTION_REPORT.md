# Documentation Integrity & Quantitative Provenance Correction Report
**Document ID**: `REPORT-DOC-CORRECTION-001`  
**Phase**: `Phase 5.1 — AUC Provenance & Public Documentation Correction`  
**Date**: `2026-09-02`  
**Status**: `CORRECTIONS APPLIED & VERIFIED`  
**Auditor**: `Antigravity Advanced Agentic Forensic System`  

---

## A. PR-AUC & ROC-AUC Provenance Verification

An exhaustive forensic trace was performed across training scripts (`train_evaluate.py`), consistency audits (`consistency_audit.py`), and serialized evaluation artifacts (`phase2_6_experiment_results.json`, `phase2_11_results.json`).

| Metric | Measured Value | Dataset Split | Model | Originating Artifact | Reproducible? | Canonical Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PR-AUC (Test)** | **0.9850** (`0.984957`) | PaySim Future Held-Out Test (Steps 378–743, N=955,744) | `Model_B_HGB` (`model_b_stateful_hgb.joblib`) | `phase2_6_experiment_results.json` (line 14846) | **YES** (`average_precision_score`) | **CANONICAL HELD-OUT TEST METRIC** |
| **PR-AUC (Val)** | **0.9405** | PaySim Validation Split (Steps 323–377, N=973,173) | `Model_B_HGB` (`model_b_stateful_hgb.joblib`) | `phase2_6_experiment_results.json` (line 43) | **YES** (`average_precision_score`) | **VALIDATION SELECTION METRIC** |
| **ROC-AUC (Test)**| **0.9998** (`0.999785`) | PaySim Future Held-Out Test (Steps 378–743, N=955,744) | `Model_B_HGB` (`model_b_stateful_hgb.joblib`) | `phase2_6_experiment_results.json` (line 14847) | **YES** (`roc_auc_score`) | **CANONICAL HELD-OUT TEST METRIC** |
| **ROC-AUC (Val)** | **0.99998** (`0.9999805`) | PaySim Validation Split (Steps 323–377, N=973,173) | `Model_B_HGB` (`model_b_stateful_hgb.joblib`) | `phase2_6_experiment_results.json` (line 44) | **YES** (`roc_auc_score`) | **VALIDATION SELECTION METRIC** |

### Decision Rule Applied:
- **PR-AUC (0.9850)** is fully verified on the future held-out test split and retained with exact split citation.
- **ROC-AUC** on the held-out test split was refined from `0.99998` (which was its validation score) to its exact test score of **`0.9998`** (`0.99979`), while explicitly noting `0.99998` on validation.

---

## B. Complete Metrics Reconciliation Matrix

The conflation between validation-selection values and future held-out test evaluation values has been eliminated. Both horizons are now explicitly distinguished across all documentation:

```
========================================================================================================================
METRIC / KPI                       VALIDATION SPLIT (STEPS 323–377)       FUTURE HELD-OUT TEST (STEPS 378–743)
========================================================================================================================
Purpose                            Threshold Selection Sweep              Frozen Out-of-Time Model Evaluation
Total Transaction Volume (N)       973,173 rows                           955,744 rows
Total Actual Malicious Transfers   570 frauds                             4,010 frauds
Operating Threshold                Sweep: θ ∈ [0.90, 0.999]               FROZEN θ* = 0.990 (Zero Tuning)
True Positives (TP)                570 (100.0% recall)                    3,996 (99.65% recall)
False Positives (FP)               119 transactions                       154 transactions
False Negatives (FN)               0 transactions (Zero Missed Fraud!)    14 transactions (0.35% count leakage)
True Negatives (TN)                972,484 clean approved                 951,580 clean approved
Precision                          82.73%                                 96.29%
Recall                             100.0%                                 99.65%
Intercepted Malicious Dollars      $769,750,597.32 (100.0%)               $6,323,408,725.18 (99.9937%)
Unintercepted Fraud Dollars (FN)   $0.00                                  $399,045.08
Flagged Clean Dollar Volume (FP)   $6,434,547.49                          $9,216,222.88
Total Realized Scenario Cost       $64,345.47 (Lowest Observed Minimum)   $491,207.31 (Realized Out-of-Time Loss)
========================================================================================================================
```

---

## C. Latency Reconciliation Across Benchmarks

All latency numbers have been mapped to their exact measurement methodologies:

```
========================================================================================================================
BENCHMARK TYPE                     REQUESTS / WORKERS    p50 (MEDIAN)    p95 LATENCY    p99 LATENCY    MAX LATENCY
========================================================================================================================
Single-Process In-Memory Engine    1,000 requests        1.75 ms         2.67 ms        3.51 ms        12.36 ms
Single-Worker Concurrent Harness   100 requests          1.21 ms–1.33 ms 2.53 ms–2.69 ms3.31 ms–4.40 ms4.40 ms
5-Worker Concurrent Harness        100 requests          15.24 ms        16.37 ms       17.71 ms       17.71 ms
10-Worker Concurrent Harness       100 requests          29.70 ms        36.82 ms       39.36 ms       39.36 ms
25-Worker Concurrent Harness       100 requests          77.50 ms        90.67 ms       94.77 ms       105.19 ms
50-Worker Concurrent Harness       100 requests          133.72 ms       172.24 ms      179.35 ms      187.45 ms
========================================================================================================================
```

### Claim-Safety Rules Enforced:
1. **35.0 ms is an internal gateway engineering budget / project target**, NOT an external Razorpay SLA guarantee.
2. Direct in-process execution executes in **3.51 ms p99** (with a multi-suite peak of **6.69 ms**).
3. The concurrency boundary is transparently disclosed: 1–5 workers easily stay within budget (<18ms); at 10+ workers on local CPU runtime, thread scheduling contention increases latency above 35ms.

---

## D. Documentation Corrections (Before vs After)

```
========================================================================================================================
LOCATION          BEFORE CORRECTION                           AFTER CORRECTION
========================================================================================================================
README.md:15      [![Tests](...106%20Tests%20Passing...)]     [![Tests](...133%20Tests%20Passing...)]
README.md:19      [![Latency](...p99%206.69%20ms...)]         [![Latency](...p99%203.51%20ms%20(Budget%2035ms)...)]
README.md:33      "guaranteeing 100% gateway uptime under     "designed to preserve gateway availability without
                  35ms"                                       dropped transactions within our 35ms internal budget"
README.md:34      "mathematically proven global cost minimum  "lowest observed scenario cost operating point across
                  across 955,744 transactions"                tested merchant friction factors"
README.md:124-126 PR-AUC: 0.9850, ROC-AUC: 0.99998, Latency:  PR-AUC: 0.9850 (future test), ROC-AUC: 0.9998 (test;
                  6.69 ms without provenance tags             0.99998 val), Latency: 3.51 ms (peak 6.69 ms)
README.md:178-188 Single table mixing Validation sweep with   Two distinct tables: Table 6.1 (Validation Selection Sweep)
                  Future Test FP/FN numbers                   and Table 6.2 (Frozen Future Held-Out Test Evaluation)
README.md:194     Column: "Typical Hackathon Submissions"     Column: "Conventional Baseline / Single-Model Approaches"
                  claiming "27%-40% Recall"                   contrasting architectural characteristics
README.md:244     "Automated Test Suite (106 Tests)"          "Automated Test Suite (133 Tests)"
README.md:303     Tree listed 106 tests and lacked Phase 4    Tree lists 133 tests and includes src/engine/infrastructure/
README.md:340-344 4 basic disclosures                         7 comprehensive institutional disclosures covering PaySim,
                                                              budget vs SLA, score calibration, Redis, and PSI
SUBMISSION.md:67  "strict 35.0 ms Gateway Target SLA Budget"  "internal 35.0 ms Gateway Engineering Budget"
SUBMISSION.md:72  "p99 Latency: 6.96 ms"                      "p99 Latency: 3.51 ms (Multi-module peak: 6.69 ms)"
SUBMISSION.md:74  "maintaining 100% gateway availability"     "designed to preserve payment availability without drops"
SUBMISSION.md:81  "Google Stitch-derived React 18 UI"         "React 18 + TypeScript Web Application"
SUBMISSION.md:82  "37 unit/SLA tests..."                      "133 unique automated unit, integration, security..."
CHECKLIST.md:35   "Google Stitch Frontend Application"        "Frontend Web Application"
CHECKLIST.md:42   "37-test master backend unit..."            "133 unique automated unit, integration, security..."
CHECKLIST.md:94   "Local in-process p99 latency (6.96 ms)"    "Local in-process p99 latency (3.51 ms, peak 6.69 ms)"
========================================================================================================================
```

---

## E. Claims Removed or Rephrased

1. **REMOVED**: *"100% gateway uptime guarantee"* $\longrightarrow$ Replaced with resilient failover description.
2. **REMOVED**: *"Razorpay SLA"* $\longrightarrow$ Replaced with internal gateway engineering budget / project target.
3. **REMOVED**: *"Typical Hackathon Submissions: 27%–40% recall"* $\longrightarrow$ Replaced with architectural comparison against conventional baseline approaches.
4. **REMOVED**: *"Google Stitch"* branding from all public markdown files.
5. **REMOVED**: *"Calibrated fraud probability"* $\longrightarrow$ Replaced with monotonic decision ranking score.
6. **REMOVED**: Single table conflating validation selection with test evaluation.

---

## F. Major Verified Claims Retained With Full Authority

1. **99.65% Fraud Recall** on held-out test ($3,996$ of $4,010$ intercepted).
2. **96.29% Precision** (Only $154$ false alarms across $955,744$ transactions).
3. **$6,323,408,725.18 Intercepted Fraud Dollars** ($99.9937\%$ dollar capture rate).
4. **$399,045.08 Missed Fraud Dollars** ($14$ false negatives).
5. **PR-AUC 0.9850** and **ROC-AUC 0.9998** on chronological future test split.
6. **Sub-15ms Circuit Breaker Fallback** to Model A Causal Baseline.
7. **Sub-Millisecond Deterministic Reason Codes** ($<0.85\text{ ms}$).
8. **Decoupled 3-Tier Policy Engine** ($\theta^* = 0.990$, $\theta_{\text{med}} = 0.900$).
9. **Tamper-Evident SHA-256 Chained Audit Ledger** with PII account masking.
10. **133 Unique Automated Tests Passing** ($100\%$ regression-free).
11. **Additive Redis State Provider & PSI Drift Engine** ($\text{PSI} = 0.0066$ STABLE).
12. **Razorpay-Compatible Pre-Capture Risk Gate & Decision Replay Studio**.

---

## G. Frozen Core Integrity Check

Every one of the 9 production-critical components was re-hashed directly from disk:

| Component Artifact | Canonical Previous SHA-256 Hash | Current Actual SHA-256 Hash | Status |
| :--- | :--- | :--- | :--- |
| `model_b_stateful_hgb.joblib` | `5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735` | `5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735` | **PASS** |
| `model_a_causal_hgb.joblib` | `ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373` | `ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373` | **PASS** |
| `policy_engine.py` | `b61ab343af0e5aa84726db1d96700b89b8e22b88a597f73c97b8320b430b9b5e` | `b61ab343af0e5aa84726db1d96700b89b8e22b88a597f73c97b8320b430b9b5e` | **PASS** |
| `decision_engine.py` | `1b5f1615f90548fa5eba94231e207d43d3e0bf7a6d68d47b802a56daaa747a4f` | `1b5f1615f90548fa5eba94231e207d43d3e0bf7a6d68d47b802a56daaa747a4f` | **PASS** |
| `feature_pipeline.py` | `41b315ed0eaff96321d7dfabab72f5fdd1a254a39604445500d545bc55a7b993` | `41b315ed0eaff96321d7dfabab72f5fdd1a254a39604445500d545bc55a7b993` | **PASS** |
| `model_manager.py` | `e2400085415e93554e480d8ff4f78fe22852c007fc5926fc27da0352d5f6899a` | `e2400085415e93554e480d8ff4f78fe22852c007fc5926fc27da0352d5f6899a` | **PASS** |
| `schemas.py` | `de16b6bba9d2b235611adf52272ff033cb40eafff6ce92c2b7de56725ff093bf` | `de16b6bba9d2b235611adf52272ff033cb40eafff6ce92c2b7de56725ff093bf` | **PASS** |
| `audit_logger.py` | `044951b6a014a07cd48179cd9d5388373ddd2b4e0dc980934db1d980e4a68afb` | `044951b6a014a07cd48179cd9d5388373ddd2b4e0dc980934db1d980e4a68afb` | **PASS** |
| `state_store.py` | `f7f6615a0277bb11631fe4dbc0be5ddde26a1c28889eff6827243946b2b70d35` | `f7f6615a0277bb11631fe4dbc0be5ddde26a1c28889eff6827243946b2b70d35` | **PASS** |

**Zero byte divergence detected across all 9 frozen core artifacts.**

---

## H. Test Suite Integrity Verification

- **Unique Automated Tests**: **133**
- **Tests Executed**: **133**
- **Passed**: **133 (100%)**
- **Failed**: **0**
- **Errors**: **0**
- **Skipped**: **0**

---

## I. Final Git Working Tree Status

```
 M FINAL_SUBMISSION_CHECKLIST.md
 M README.md
 M SUBMISSION.md
 M src/engine/api.py
?? research/final_competition/DOCUMENTATION_CORRECTION_REPORT.md
?? research/final_competition/README_FORENSIC_AUDIT.md
?? research/phase4/
?? research/phase_p4_hardening/
?? src/engine/infrastructure/
?? tests/test_concurrent_load.py
?? tests/test_drift_monitoring.py
?? tests/test_redis_state_store.py
?? tests/test_security_auth.py
```

---

## J. Final Verdict

### **DOCUMENTATION PASS — FULLY DEFENSIBLE**

The Risk Sentinel public documentation has achieved complete technical integrity:
1. Every quantitative number is directly traced to an empirical artifact.
2. The validation selection sweep and the future held-out test evaluation are cleanly separated.
3. Internal engineering budgets are clearly distinguished from external payment gateway SLAs.
4. Over-promised absolute availability claims have been replaced with precise engineering descriptions.
5. All 9 core ML artifacts remain 100% frozen and cryptographically verified.
6. The entire 133-test regression suite passes with 0 errors.

**Phase 5.1 is officially complete. STOPPING HERE.**
