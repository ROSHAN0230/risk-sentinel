# Implementation Plan — Risk Sentinel Phase 2.13: Full-Stack Integration & End-to-End Verification

This plan outlines the end-to-end integration and automated verification of the complete Risk Sentinel application across all layers:
`Frontend (React/TypeScript)` $\leftrightarrow$ `FastAPI REST Layer` $\leftrightarrow$ `RiskDecisionEngine` $\leftrightarrow$ `Model B / Model A Fallback` $\leftrightarrow$ `InMemoryStateStore` $\leftrightarrow$ `Policy Engine` $\leftrightarrow$ `Explanation Resolver` $\leftrightarrow$ `Immutable Audit Logger`.

---

## 1. Scope & Verification Targets

1. **Reconciliation & Diff Audit**:
   - Verify that zero frozen backend ML logic, thresholds, or API semantics have changed.
2. **Primary Route Verification**:
   - `/dashboard` (Executive Risk Overview)
   - `/stream` (Real-Time In-Flight Stream + Demo Launcher)
   - `/inspector/:tx_id` (Deep-Dive Causal Attribution Inspector)
   - `/audit` (Immutable Regulatory Decision Ledger)
   - `/benchmarks` (Research Forensics & Cost Sensitivity Lab)
3. **End-to-End Demo Fixture Execution (`DEMO-01` to `DEMO-09`)**:
   - Verify that every demo scenario executes through the actual UI $\to$ API $\to$ DecisionEngine $\to$ Response path and renders bitwise-accurate scores, bands, actions, reason codes, and causal evidence.
4. **Failure State Resilience**:
   - Backend unavailable / network timeout
   - State-store timeout / forced failure $\to$ Model A Fallback
   - Corrupted model binary $\to$ Startup halt with `ModelIntegrityError`
   - Empty audit ledger handling
   - Malformed input schema validation (HTTP 422)
5. **Truth Boundary Assertions**:
   - No "99% probability of fraud" claims
   - No post-transaction balance gap references
   - Clear visual partitioning of Live Engine vs Benchmark vs Demo data tiers
   - Latency explicitly separated into Local Benchmark (2.40ms / 3.97ms) vs Gateway SLA Budget (35.0ms)

---

## 2. Deliverables Layout in `research/phase2_13/`

```
research/phase2_13/
├── implementation_plan.md                 # Implementation plan
├── FINAL_REPORT.md                        # Master full-stack verification report
├── walkthrough.md                         # Walkthrough and startup guide
├── e2e_verification.md                    # Automated end-to-end test execution report
├── manual_test_matrix.md                  # Comprehensive manual test case matrix (18 test cases)
└── artifacts/
    ├── e2e_demo_results.json              # Machine-readable output for all 9 demo scenarios
    └── full_stack_test_summary.json       # Master test summary JSON
```

---

## 3. Verification Plan

1. Execute full automated backend test suite (`python tests/run_all_tests.py`).
2. Execute Phase 2.10 adversarial audit suite (`python research/phase2_10/audit_suite_phase2_10.py`).
3. Execute Phase 2.11 cross-phase consistency audit (`python research/phase2_11/consistency_audit.py`).
4. Execute Phase 2.13 End-to-End Integration Test Runner (`python research/phase2_13/e2e_integration_test.py`).
5. Re-run `npm run build` in `frontend/` to ensure zero compilation or bundle errors.
