# Walkthrough — Risk Sentinel Phase 2.7: Adversarial Model Integrity & Operating-Policy Audit

All Phase 2.7 audit modules have been executed and verified in an isolated research environment (`research/phase2_7/`).

---

## 1. Executed Audit Modules & Artifacts

| Audit Module | Script | Output Artifact | Key Finding |
| :--- | :--- | :--- | :--- |
| **Audit 1: Training Integrity** | [`audit.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/audit.py) | [`audit_training_isolation.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/audit_training_isolation.json) | Train (1-322), Val (323-377), Test (378-743) strictly disjoint. Zero overlap or future leakage. |
| **Audit 2: Score Distribution** | [`score_analysis.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/score_analysis.py) | [`score_distribution.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/score_distribution.json) | Threshold $0.99$ explained by $+7.106$ Bayesian logit shift from `class_weight='balanced'`. |
| **Audit 3: Threshold Sensitivity**| [`threshold_sensitivity.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/threshold_sensitivity.py) | [`threshold_sensitivity.csv`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/threshold_sensitivity.csv) | $\theta = 0.99$ achieves global cost minimum (\$64,345.47) with 100% recall on validation. |
| **Audit 4: Cost Function Audit** | [`cost_audit.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/cost_audit.py) | [`cost_audit.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/cost_audit.json) | Cost formula is dimensionally consistent, non-double-counting, and framed as sensitivity bounds. |
| **Audit 5: Model Convergence** | [`convergence_analysis.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/convergence_analysis.py) | [`model_convergence.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/model_convergence.json) | Model A & B converge because 99.85% of PaySim senders are single-use disposable IDs. |
| **Audit 6: PaySim Shortcuts** | [`shortcut_analysis.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/shortcut_analysis.py) | [`shortcut_analysis.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/shortcut_analysis.json) | $97.82\%$ of fraud is an exact $100\%$ balance liquidation (`oldbalanceOrg == amount`). |
| **Audit 7: Policy Analysis** | [`policy_analysis.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/policy_analysis.py) | [`policy_analysis.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/policy_analysis.json) | Three-tier policy intercepts $99.99\%$ of fraud dollars with $0.016\%$ FPR on future test. |
| **Master Orchestrator** | [`run_phase2_7.py`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/run_phase2_7.py) | [`phase2_7_results.json`](file:///c:/Users/raahe/Downloads/razorpay/research/phase2_7/artifacts/phase2_7_results.json) | End-to-end execution completed in 364.00 seconds. |

---

## 2. Core Numerical Verification Table (Future Test: Steps 378–743)

```
========================================================================================
METRIC                             MODEL A (Baseline)          MODEL B (Stateful HGB)
========================================================================================
Future Test PR-AUC                 0.98431                     0.98496 (+0.00065)
Future Test ROC-AUC                0.99976                     0.99979 (+0.00003)
Operating Threshold                0.98                        0.99
Precision                          96.29% (3,996 / 4,150)      96.29% (3,996 / 4,150)
Recall                             99.65% (3,996 / 4,010)      99.65% (3,996 / 4,010)
F1-Score                           0.97941                     0.97941
False Positive Rate (FPR)          0.000162 (0.0162%)          0.000162 (0.0162%)
False Negative Rate (FNR)          0.003491 (0.349%)           0.003491 (0.349%)
True Positives (TP)                3,996                       3,996
False Positives (FP)               154                         154
True Negatives (TN)                951,580                     951,580
False Negatives (FN)               14                          14
Fraud Dollars Detected             $6,323,408,725.18 (99.99%)  $6,323,408,725.18 (99.99%)
Fraud Dollars Missed (FN Loss)     $399,045.08                 $399,045.08
Flagged Non-Fraud Volume (FP Vol)  $9,216,222.88               $9,216,222.88
Total Cost (at 1.0% FP Penalty)    $491,207.31                 $491,207.31
========================================================================================
```

---

## 3. Decision Matrix for Phase 2.8+ Engine Design

1. **Model B (Stateful HistGradientBoosting)**: **KEEP**. Foundational for production velocity and mule detection.
2. **Model A (Causal Baseline)**: **KEEP**. Active benchmark and fallback engine.
3. **Threshold $\theta^* = 0.99$**: **KEEP (WITH CALIBRATION DISCLAIMER)**. Mathematically validated under balanced class weighting.
4. **Three-Tier Decision Framework**: **KEEP**. High-precision tiering ($\ge 0.99$ Decline/Step-Up, $0.90–0.99$ 2FA/Review, $<0.90$ Approve).
5. **Hard-Rule Channel Bypass**: **NEEDS DISCLAIMER**. Valid for PaySim; label as dataset-specific empirical rule.
6. **Financial Cost Equation**: **KEEP (AS SENSITIVITY BOUNDS)**. Dimensionally sound.
7. **PaySim Benchmark Role**: **KEEP (WITH SYNTHETIC DISCLAIMER)**. Suitable with documented sender ephemerality.
