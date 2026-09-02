# Walkthrough — Risk Sentinel Phase 2.13: Full-Stack Integration & End-to-End Verification

All end-to-end integration tests, manual test matrices, and demo verifications for Phase 2.13 are complete and documented under `research/phase2_13/`.

---

## 1. Summary of Accomplishments

1. **Reconciliation Audit**: Confirmed zero modifications to frozen ML models, features, thresholds ($\theta_{\text{high}}=0.990, \theta_{\text{med}}=0.900$), policy logic, explanation logic, or audit semantics.
2. **Full-Stack Execution**: Verified seamless end-to-end communication from the React 18 UI through FastAPI REST endpoints to the synchronous `RiskDecisionEngine`.
3. **9 Demo Scenarios (`DEMO-01` to `DEMO-09`)**: Verified that every demo scenario executes through the actual live HTTP pipeline and returns accurate scores, bands, actions, and causal explanations.
4. **Resilience & Fallback**: Verified that state store outages immediately trip the circuit breaker in $<15\text{ms}$ to evaluate via Model A (Causal Baseline) without 500 errors.
5. **Audit Ledger Chaining**: Verified that decisions emit tamper-evident SHA-256 chained events with masked account numbers (`C192***465`).

---

## 2. Quick-Start Guide for Judges & Operators

### Launch the Application (Single Command):
```bash
python -m uvicorn src.engine.api:app --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000` in your web browser.

### Key Interactive Flows to Demo:
1. **Executive Dashboard (`/dashboard`)**: View top KPI cards with clear data tier labeling (`Live Engine` vs `Benchmark / Research`).
2. **Demo Preset Launcher (`/stream`)**: Click `[DEMO-03 Critical Balance Drain]` to see real-time automated decline in $<3\text{ms}$.
3. **Deep-Dive Inspector (`/inspector/:tx_id`)**: Inspect the radial risk gauge, action banner, primary reason badge, and 2x3 causal evidence grid.
4. **Immutable Audit Ledger (`/audit`)**: Inspect cryptographically chained SHA-256 blocks with PII masking.
5. **Research Forensics (`/benchmarks`)**: Move the interactive cost sensitivity slider ($\alpha$) to see how operating threshold $\theta^* = 0.990$ minimizes total financial loss.
