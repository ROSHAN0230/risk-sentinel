# Risk Sentinel — Google Stitch Master UI/UX Handoff Specification
**Document ID**: `STITCH-HND-2.11-001`  
**Status**: `FROZEN UI DESIGN HANDOFF`  
**Product**: `Risk Sentinel — AI Risk Manager (Razorpay Defensive Fraud Track)`  

---

## 1. Product Identity, Purpose & Target Persona

- **Product Name**: **Risk Sentinel**
- **Tagline**: Real-Time Causal Risk Decision Engine & Explainable Loss Defense
- **Core Value Proposition**: Intercepts $>99.99\%$ of fraudulent financial loss in real time ($<35\text{ms}$ latency) using strictly causal, stateful machine learning, sub-millisecond deterministic explanations, and zero-downtime fallback resilience.
- **Target User Personas**:
  1. **Fraud Operations Analyst**: Investigates flagged transactions, evaluates reason codes, and reviews evidence grids.
  2. **Risk Engineering Lead**: Monitors gateway latency, throughput, model fallback telemetry, and circuit breakers.
  3. **Compliance & Audit Officer**: Verifies decision reproducibility, PII masking, and cryptographic SHA-256 audit chains.
  4. **Hackathon / Viva Judge**: Evaluates academic rigor, causal integrity, financial cost curves, and demo scenario reliability.

---

## 2. Information Architecture & Primary Screen Flow

The Google Stitch UI is structured around **5 Core Screens / Views**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RISK SENTINEL APP BAR                           │
│  [Logo] Risk Sentinel | Live Gateway: HEALTHY | Model B (Active) | 3.9ms│
├───────────────┬────────────────────────────────────────────────────────┤
│ NAVIGATION    │ PRIMARY VIEWPORT                                       │
│               │                                                        │
│ 1. Overview   │ ──> Executive KPI Cards (PR-AUC, Dollars Saved, Latency)│
│ 2. Live Stream│ ──> In-Flight Transaction Feed + Live Simulator        │
│ 3. Inspector  │ ──> Deep-Dive Decision, Causal Evidence & Reason Tree   │
│ 4. Audit Log  │ ──> Cryptographically Chained Immutable Decision Ledger│
│ 5. Benchmarks │ ──> PaySim Forensics, ROC/PR Curves, Cost Sensitivity  │
└───────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Screen-by-Screen UI Component Specifications

### Screen 1: Executive Risk Dashboard (`/dashboard`)
- **Top KPI Ribbon (4 Metric Cards)**:
  1. **Fraud Intercept Rate**: `99.99%` (\$6.32B protected / \$399k missed).
  2. **Precision on High-Risk**: `96.29%` (FPR: 0.0162% / 16 per 100k).
  3. **Decision Latency (p99)**: `3.97 ms` (Local Core) / `35 ms` (Gateway SLA).
  4. **System Resilience**: `100.0%` (Zero dropped requests; Model A fallback active).
- **Traffic Volume Breakdown**: Bar chart showing `APPROVE` ($99.98\%$), `CHALLENGE` ($0.01\%$), `DECLINE` ($0.01\%$).
- **Active Channel Distribution**: High-risk scored channels (`TRANSFER`, `CASH_OUT`) vs fast-path empirical bypass channels.

---

### Screen 2: Real-Time Transaction Stream & Live Simulator (`/stream`)
- **Live Event Table**: Scrolling real-time table of evaluated transactions showing:
  - Timestamp, Masked Transaction ID, Type Badge, Amount, Masked Sender, Masked Dest, Score, Band Badge, Action Badge.
- **Interactive Simulation Controls (9 Demo Scenario Presets)**:
  - Quick-load buttons for: `[DEMO-01: Normal Payment]`, `[DEMO-02: Suspicious Drain]`, `[DEMO-03: Critical Drain]`, `[DEMO-04: Cold Start]`, `[DEMO-05: Fallback Mode]`, etc.
  - Interactive "Inject Custom Transaction" form with real-time JSON preview.

---

### Screen 3: Deep-Dive Transaction Inspector (`/inspector/:tx_id`)
*This is the centerpiece screen for judge evaluations and fraud analyst reviews.*
- **Top Summary Banner**:
  - `Risk Score`: Radial meter displaying score (e.g. `0.9984`).
  - `Risk Band`: Pill badge (`HIGH_RISK` / `MEDIUM_RISK` / `LOW_RISK`).
  - `Action Enforced`: Bold status banner (`DECLINE` in Crimson Red / `STEP_UP_CHALLENGE` in Amber / `APPROVE` in Emerald Green).
- **Causal Explanation Card**:
  - **Primary Reason Badge**: e.g., `CRITICAL: 100% Balance Liquidation`.
  - **Analyst Narrative**: Formatted plain-English summary.
  - **Causal Evidence Grid (2x3 Key-Value Matrix)**:
    - Amount: `\$284,100.50`
    - Sender Balance Prior: `\$284,100.50`
    - Liquidity Drain: `100.0%`
    - Channel: `TRANSFER`
    - Sender History Depth: `0 prior txs (Cold Start)`
    - Destination Mule Velocity: `3 prior incoming txs`
- **Engine Telemetry Pill**: Displays Model Used (`MODEL_B_STATEFUL_HGB` or `MODEL_A_FALLBACK`), Execution Latency (`2.26 ms`), and Operating Threshold applied (`0.990`).

---

### Screen 4: Immutable Audit Trail & Regulatory Ledger (`/audit`)
- **Chained Event Viewer**: Expandable timeline of immutable audit events.
- **Integrity Validation Badge**: Displays SHA-256 block hash chaining confirmation (`Hash Verified: sha256:e3b0c44...`).
- **PII Masking Preview**: Visual demonstration that customer accounts are rendered as `C192***465` to satisfy GDPR/PCI compliance.

---

### Screen 5: Research Benchmarks & Cost Sensitivity Explorer (`/benchmarks`)
- **Validation vs Future Test Comparison Table**: Side-by-side metrics table for Model A vs Model B.
- **Cost Sensitivity Curve**: Interactive slider for $\alpha \in [0.1\%, 5.0\%]$ showing Total Loss vs Operating Threshold.
- **PaySim Forensics & Limitation Disclosures**: Dedicated card explaining synthetic sender ephemerality ($99.85\%$ single-use) and balance drain concentration.

---

## 4. Visual Design Language & Color Tokens

- **Theme**: Premium Dark Mode with High-Contrast Status Tokens.
- **Color Palette**:
  - **Surface Background**: `#0F172A` (Slate 900)
  - **Card Surface**: `#1E293B` (Slate 800) / Border: `#334155` (Slate 700)
  - **Primary Brand / Accent**: `#3B82F6` (Electric Blue / Razorpay Blue)
  - **Action: APPROVE / Low Risk**: `#10B981` (Emerald Green)
  - **Action: STEP_UP / Medium Risk**: `#F59E0B` (Amber / Gold)
  - **Action: DECLINE / High Risk**: `#EF4444` (Crimson Red)
  - **Status: Fallback Engine Active**: `#6366F1` (Indigo Purple)
  - **Text Primary**: `#F8FAFC` (Slate 50)
  - **Text Secondary**: `#94A3B8` (Slate 400)

---

## 5. Strict Terminology Rules (What to Use vs What to Avoid)

| Recommended Terminology (MUST USE) | Prohibited Terminology (DO NOT USE) |
| :--- | :--- |
| **"Operating Risk Score (0.990)"** | *"99% Probability of Fraud"* |
| **"Causal Point-in-Time Features"** | *"Post-transaction balance gap / delta"* |
| **"Decoupled Policy Action (Decline/Step-Up)"** | *"Model-decided decline"* |
| **"Stateful Behavioral Context"** | *"Leaked future history"* |
| **"Model A Graceful Fallback"** | *"System crash / failure state"* |
| **"PaySim Empirical Channel Bypass"** | *"Universal rule that Payment is safe"* |
| **"Scenario Sensitivity Analysis ($\alpha$)"** | *"Actual Razorpay financial loss"* |
