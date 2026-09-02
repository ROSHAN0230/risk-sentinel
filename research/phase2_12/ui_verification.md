# Risk Sentinel — UI Verification & Test Report
**Document ID**: `UI-VER-2.12-001`  
**Status**: `VERIFIED & FROZEN`  
**Frontend Version**: `v2.12.0` | `React 18 + TypeScript + TailwindCSS + Vite`  
**Stitch Integration**: `Project ID: 3908244755188985568` | `Asset: assets/429e5ca2ba1e44daa23450e7e1a38ae4`  

---

## 1. Automated Verification Suite Execution

```
==================================================================================================
VERIFICATION STAGE               TOOL / COMMAND                   RESULT / DETAILS
==================================================================================================
1. Google Stitch Generation      Stitch MCP Project 3908244755188985568 5 Screens & Design System Generated
2. TypeScript Type Check         tsc (strict mode)                PASSED (0 errors)
3. Production Bundle Build       vite build (dist/)               PASSED (Built in 25.66s, 235 kB gzip total)
4. Backend Test Suite            python tests/run_all_tests.py    PASSED (37/37 tests passed, 100%)
5. Adversarial Audit Suite       python research/phase2_10/audit_suite_phase2_10.py PASSED (8/8 audits passed)
6. Consistency Audit             python research/phase2_11/consistency_audit.py     PASSED (0 discrepancies)
7. Fast-Path / Scored Channels   Live API Evaluation              PASSED (Bypass on PAYMENT, Scored on TRANSFER)
8. 9 Demo Scenario Presets       DEMO-01 to DEMO-09 Fixtures      PASSED (All bitwise-matched decision outcomes)
==================================================================================================
OVERALL VERIFICATION STATUS:     100% PASSED — READY FOR FULL-STACK INTEGRATION REVIEW (PHASE 2.13)
==================================================================================================
```

---

## 2. Component & Screen Inventory

### Reusable UI Components (`frontend/src/components/`)
1. `Navbar.tsx`: Sticky navigation bar with Gateway Health pulse, active model pill, and responsive navigation links.
2. `DataSourceBadge.tsx`: Visual tags distinguishing `LIVE ENGINE`, `BENCHMARK / RESEARCH`, and `DEMO SCENARIO`.
3. `DecisionBadge.tsx`: High-contrast action pills (`APPROVE` in Emerald, `STEP-UP 2FA` in Amber, `MANUAL REVIEW` in Yellow, `DECLINE` in Crimson).
4. `RiskBandBadge.tsx`: Standardized `LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK` badges.
5. `RiskScoreGauge.tsx`: Segmented progress bar with numeric readout and explicit threshold markers ($\theta_{\text{med}} = 0.900, \theta_{\text{high}} = 0.990$).
6. `ReasonCodeCard.tsx`: Primary reason badge, plain-English summary, factor tags, and fallback mode warning.
7. `CausalEvidenceGrid.tsx`: 2x3 matrix of point-in-time features (Amount, Sender Old Balance, Liquidity Drain %, Channel, Sender Context, Recipient Inflow).
8. `EngineTelemetry.tsx`: Strip showing model type, execution latency, threshold applied, and version.
9. `DemoScenarioSelector.tsx`: Interactive launcher with 9 instant-load preset cards.
10. `AuditTimeline.tsx`: Expandable timeline of tamper-evident SHA-256 chained blocks with PII masking (`C192***465`).
11. `BenchmarkMetricCard.tsx`: Metric card with data source badge and historical context subtext.
12. `DisclaimerBanner.tsx`: Compliance truth boundary footer.

### Implemented Screen Views (`frontend/src/pages/`)
1. **`/dashboard` (`DashboardPage.tsx`)**: Executive KPI ribbon (99.99% Dollars Protected, 96.29% Precision, 2.40ms Latency, 100% Resilience), traffic volume breakdown, and active channel routing architecture.
2. **`/stream` (`StreamPage.tsx`)**: In-flight scrolling transaction feed, 9 demo scenario presets, and custom transaction evaluation form.
3. **`/inspector/:tx_id` (`InspectorPage.tsx`)**: Deep-dive decision inspector with radial risk gauge, action banner, causal evidence grid, and engine telemetry.
4. **`/audit` (`AuditPage.tsx`)**: Immutable regulatory decision ledger with SHA-256 block hash validation and PII masking.
5. **`/benchmarks` (`BenchmarksPage.tsx`)**: Side-by-side Model A vs Model B comparison, interactive financial cost sensitivity slider ($\alpha \in 0.1\%-5.0\%$), and PaySim forensic disclosures.

---

## 3. Strict Truth Boundary & Terminology Verification

- [x] **No Uncalibrated Probability Claims**: Scores are labeled as "Operating Risk Score (0.990)" and never as "99% probability of fraud."
- [x] **No Post-Transaction Balances**: The UI displays strictly point-in-time balances (`oldbalanceOrg`, `oldbalanceDest`) with zero mentions of `newbalanceOrig` or `orig_gap`.
- [x] **Clear Data Origin Badges**: Every metric card and screen displays its data tier (`Live Engine` vs `Benchmark / Research` vs `Demo Scenario`).
- [x] **Separated Latency Disclaimers**: Local benchmark is labeled as "Local benchmark: p99 2.40 ms / 3.97 ms" and gateway SLA is labeled as "Gateway SLA budget: 35.0 ms".
- [x] **Benchmark Dollar Results Tagged**: 99.99% dollars protected is labeled as "PaySim Benchmark Result (Steps 378–743)", not as a live production KPI.
