# Walkthrough — Risk Sentinel Phase 2.12: Google Stitch UI Implementation & Integration

All components, pages, Stitch design systems, and frontend builds for Phase 2.12 have been implemented and verified under `frontend/` and `research/phase2_12/`.

---

## 1. Directory Structure

```
razorpay/
├── frontend/                              # Production Web UI
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   ├── dist/                              # Production compiled bundles (235 kB gzip)
│   └── src/
│       ├── api/client.ts                  # REST client for FastAPI endpoints
│       ├── types/engine.ts                # TypeScript types mirroring schemas.py
│       ├── components/
│       │   ├── Navbar.tsx
│       │   ├── RiskScoreGauge.tsx
│       │   ├── DecisionBadge.tsx
│       │   ├── RiskBandBadge.tsx
│       │   ├── ReasonCodeCard.tsx
│       │   ├── CausalEvidenceGrid.tsx
│       │   ├── EngineTelemetry.tsx
│       │   ├── DemoScenarioSelector.tsx
│       │   ├── AuditTimeline.tsx
│       │   ├── BenchmarkMetricCard.tsx
│       │   ├── DisclaimerBanner.tsx
│       │   └── DataSourceBadge.tsx
│       ├── pages/
│       │   ├── DashboardPage.tsx          # /dashboard view
│       │   ├── StreamPage.tsx             # /stream view with 9 demo presets
│       │   ├── InspectorPage.tsx          # /inspector/:tx_id deep-dive view
│       │   ├── AuditPage.tsx              # /audit immutable ledger view
│       │   └── BenchmarksPage.tsx         # /benchmarks research lab view
│       ├── App.tsx
│       └── main.tsx
└── research/phase2_12/
    ├── implementation_plan.md
    ├── FINAL_REPORT.md
    ├── walkthrough.md
    └── ui_verification.md
```

---

## 2. Running the Full Application

### Option A: Unified FastAPI Server (Serves API + UI)
```bash
python -m uvicorn src.engine.api:app --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000` in your browser to access the complete application.

### Option B: Frontend Dev Mode (Hot-Reload)
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` with automatic proxying to backend on port 8000.

---

## 3. Verification Summary

- [x] `npm run build`: Success (0 TypeScript errors).
- [x] `python tests/run_all_tests.py`: 37 / 37 passed.
- [x] `python research/phase2_10/audit_suite_phase2_10.py`: 8 / 8 passed.
- [x] `python research/phase2_11/consistency_audit.py`: 0 discrepancies.
- [x] `DEMO-01` to `DEMO-09`: Working cleanly in interactive launcher.
