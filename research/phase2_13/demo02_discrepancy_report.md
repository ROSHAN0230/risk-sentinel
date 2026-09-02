# Risk Sentinel — DEMO-02 Discrepancy & Root Cause Audit Report
**Document ID**: `DISC-DEMO02-2.13-001`  
**Date**: `2026-08-31`  
**Status**: `INVESTIGATED & ROOT CAUSE ISOLATED`  

---

## 1. Discrepancy Description

- **Phase 2.10/2.11 Contract (`DEMO_CONTRACT.md`, `demo_scenarios.md`)**:
  - Scenario ID: `DEMO-02` (*"Suspicious Severe Liquidity Outflow"*)
  - Hand-Crafted Input Fixture:
    ```json
    {
      "transaction_id": "tx-demo-02",
      "step": 451,
      "type": "TRANSFER",
      "amount": 9500.00,
      "nameOrig": "C_BOB_02",
      "oldbalanceOrg": 10000.00,
      "nameDest": "C_NEW_DEST_02",
      "oldbalanceDest": 500.00
    }
    ```
  - Documented Expectation: `MEDIUM_RISK` $\implies$ `STEP_UP_CHALLENGE` / `CHALLENGED` with `RC_SEVERE_LIQUIDITY_DRAIN`.
- **Phase 2.13 E2E Integration Observation**:
  - Live Model B Evaluation: `Score = 0.00179` $\implies$ `LOW_RISK` $\implies$ `APPROVED`.

---

## 2. Comprehensive Trace & Root Cause Analysis

We performed a line-by-line trace across the system:
`DEMO_CONTRACT.md` $\to$ `demo_scenarios.md` $\to$ `frontend/src/api/client.ts` $\to$ `POST /v1/risk/evaluate` $\to$ `RiskDecisionEngine` $\to$ `Model B HGB Classifier`.

### Findings:
1. **The ML Model, Feature Pipeline, Policy Engine, and Thresholds are 100% Unchanged and Correct**:
   - `model_b_stateful_hgb.joblib` SHA-256 is `5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735` (identical to Phase 2.8/2.9 freeze).
   - Operating thresholds $\theta_{\text{high}} = 0.990, \theta_{\text{med}} = 0.900$ are intact.
   - Policy Engine mapping for `MEDIUM_RISK` is intact:
     - `amount < $50,000` $\implies$ `CHALLENGED` / `STEP_UP_CHALLENGE`
     - `amount >= $50,000` $\implies$ `REVIEW_REQUIRED` / `MANUAL_REVIEW`
2. **Root Cause: Hand-Crafted Synthetic Fixture was Never Evaluated against the Trained Decision Trees during Phase 2.10 Draft**:
   - In Phase 2.10, when designing the 9 demo scenarios, the author manually authored synthetic numbers (`amount: 9500.0, oldbalanceOrg: 10000.0`) under the assumption that draining 95% of \$10,000 would produce a score in $[0.90, 0.99)$.
   - However, in the PaySim dataset (and consequently in the trained GBDT trees), fraud attacks almost never occur at low amounts with remaining balance; 97.82% of all frauds are 100% complete liquidations of large balances.
   - Therefore, the trained decision trees assign low amounts (\$9,500) with remaining balance (\$500) to a low-risk leaf with raw score $\approx 0.00179$.
3. **Audit Suite Silent Passage in Phase 2.10**:
   - In Phase 2.10 `audit_suite_phase2_10.py` (Audit 8), the test executed `engine.evaluate(req)` and saved the output to `demo_scenarios_results.json` without asserting a specific decision enum.
   - In Phase 2.11 `DEMO_CONTRACT.md`, the documentation copied the narrative specification from `demo_scenarios.md` rather than the model's actual output.
   - In Phase 2.13 `e2e_integration_test.py`, the test asserted the live model return value (`0.0018 -> APPROVED`), exposing the latent inconsistency.

---

## 3. Empirical Evidence & Grounded Solution

We scanned the validation and held-out test splits to identify transactions that genuinely evaluate into the `MEDIUM_RISK` band ($0.9000 \le S < 0.9900$) in the frozen Model B.

### Validated Empirical Medium-Risk Transaction (Step 324, Validation Split):
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

### Exact Engine Evaluation Output:
- **Operating Risk Score**: `0.983023` (strictly in $[0.9000, 0.9900)$)
- **Risk Band**: `MEDIUM_RISK`
- **Decoupled Decision**: `REVIEW_REQUIRED` (since amount $> \$50,000$)
- **Policy Action**: `MANUAL_REVIEW`
- **Primary Reason Code**: `RC_SEVERE_LIQUIDITY_DRAIN`
- **Causal Evidence**:
  - `amount`: \$976,662.30
  - `oldbalanceOrg`: \$982,857.46
  - `liquidation_pct`: 99.37%
  - `channel`: `TRANSFER`
  - `is_sender_cold_start`: 1

---

## 4. Reconciliation Plan

1. **Update DEMO-02 Fixture in Contracts & Code**:
   - Update `frontend/src/api/client.ts` fixture `DEMO-02` with the verified empirical values (`amount: 976662.30, oldbalanceOrg: 982857.46, nameOrig: "C1959219454", nameDest: "C2061756973", oldbalanceDest: 2453029.29`).
   - Update `research/phase2_10/demo_scenarios.md` and `research/phase2_10/audit_suite_phase2_10.py` to use the verified empirical fixture.
   - Update `research/phase2_11/DEMO_CONTRACT.md` to reflect `MEDIUM_RISK` $\implies$ `REVIEW_REQUIRED` / `MANUAL_REVIEW` with `RC_SEVERE_LIQUIDITY_DRAIN`.
   - Update `research/phase2_13/e2e_integration_test.py` with the reconciled expected values.
2. **Re-Run All Verification Suites**:
   - `python research/phase2_10/audit_suite_phase2_10.py`
   - `python research/phase2_11/consistency_audit.py`
   - `python research/phase2_13/e2e_integration_test.py`
   - `npm run build` in `frontend/`
3. **Report Outcome to User and Await Review**.
