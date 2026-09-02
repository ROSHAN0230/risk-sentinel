# Implementation Plan — Risk Sentinel Phase 2.12: Google Stitch UI Implementation & Integration

This plan details the implementation of the **Risk Sentinel Web UI** derived from the Google Stitch design system (Project ID: `3908244755188985568`, Asset ID: `assets/429e5ca2ba1e44daa23450e7e1a38ae4`) and integrated with the frozen backend (`src/engine/api.py`).

---

## 1. Objectives & Scope

1. **Google Stitch MCP Execution**:
   - Utilize generated Stitch design themes, layout grids, color tokens (`#0F172A` Slate Dark, `#1E293B` Surface, `#3B82F6` Electric Blue, `#10B981` Emerald, `#EF4444` Crimson), and screens.
2. **5 Primary Experiences**:
   - `/dashboard`: Executive Risk Overview with live engine vs benchmark telemetry.
   - `/stream`: In-flight transaction stream with filters and interactive 9-scenario demo launcher (`DEMO-01` to `DEMO-09`).
   - `/inspector/:tx_id`: Deep-dive transaction inspector with radial risk gauge, action banner, primary reason badge, narrative, and 2x3 causal evidence matrix.
   - `/audit`: Immutable decision ledger with SHA-256 block hash validation and PII masking.
   - `/benchmarks`: Research forensics, cost sensitivity slider ($\alpha \in 0.1\%-5.0\%$), and PaySim limitation disclosures.
3. **Component System**:
   - `RiskScoreGauge`, `DecisionBadge`, `RiskBandBadge`, `ReasonCodeCard`, `CausalEvidenceGrid`, `EngineTelemetry`, `TransactionRow`, `DemoScenarioSelector`, `AuditTimeline`, `BenchmarkMetricCard`, `DisclaimerBanner`, `DataSourceBadge`.
4. **API Integration Service**:
   - Clean client connecting to `POST /v1/risk/evaluate`, `GET /v1/health`, `GET /v1/audit/events`, `GET /v1/model/info`.
5. **Truth Boundaries & Labeling**:
   - Clear visual tags distinguishing `LIVE ENGINE DATA`, `BENCHMARK / RESEARCH DATA`, and `DEMO SCENARIO DATA`.
   - Explicit latency separation: "Local benchmark: p99 2.40ms / 3.97ms" vs "Gateway SLA budget: 35ms".

---

## 2. Directory Layout

```
razorpay/
├── frontend/                              # Web application
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts                  # REST API client for FastAPI
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── RiskScoreGauge.tsx
│   │   │   ├── DecisionBadge.tsx
│   │   │   ├── RiskBandBadge.tsx
│   │   │   ├── ReasonCodeCard.tsx
│   │   │   ├── CausalEvidenceGrid.tsx
│   │   │   ├── EngineTelemetry.tsx
│   │   │   ├── DemoScenarioSelector.tsx
│   │   │   ├── AuditTimeline.tsx
│   │   │   ├── BenchmarkMetricCard.tsx
│   │   │   ├── DisclaimerBanner.tsx
│   │   │   └── DataSourceBadge.tsx
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── StreamPage.tsx
│   │   │   ├── InspectorPage.tsx
│   │   │   ├── AuditPage.tsx
│   │   │   └── BenchmarksPage.tsx
│   │   ├── types/
│   │   │   └── engine.ts                  # TypeScript types matching schemas.py
│   │   ├── App.tsx
│   │   └── main.tsx
└── research/phase2_12/
    ├── implementation_plan.md
    ├── FINAL_REPORT.md
    ├── walkthrough.md
    ├── ui_verification.md
    └── artifacts/
```

---

## 3. Verification Plan

1. Frontend type checking and production build (`npm run build`).
2. Verification of all 5 view routes.
3. Backend automated test suite execution (`python tests/run_all_tests.py`).
4. End-to-end evaluation of `DEMO-01` through `DEMO-09` against live API.
