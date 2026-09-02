# Risk Sentinel — Judge & Viva Demo Walkthrough Guide

> **2-Minute Competition Demonstration & Oral Defense Guide**  
> *Track: Razorpay AI Risk Manager / AI Builder Intern Track*

---

## 1. Quick Launch

```bash
# Start the full-stack server and open browser
python run_demo.py
```
Open **`http://localhost:8000`** in your browser.

---

## 2. 2-Minute Judge Walkthrough Script

```
┌─────────────────────────┬─────────────────────────────────────────────────────────────┬───────────────────────────────────────────┐
│ STEP                    │ WHAT TO CLICK / SHOW ON SCREEN                              │ TALKING POINT / VIVA DEFENSE              │
├─────────────────────────┼─────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
│ 1. Overview             │ Top Navigation -> "Executive Risk Overview"                 │ "Risk Sentinel decouples ML risk scoring  │
│    (30 seconds)         │ Highlight the 4 KPI cards and explicit Data Source Badges   │ from operational actions. Notice the      │
│                         │ (LIVE ENGINE vs BENCHMARK / RESEARCH).                      │ distinction between benchmark research     │
│                         │                                                             │ and live engine latency."                 │
├─────────────────────────┼─────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
│ 2. Demo Presets         │ Top Navigation -> "Transaction Stream & Simulation"         │ "We have 9 pre-configured judge fixtures  │
│    (45 seconds)         │ Click `DEMO-01` (Normal Payment):                           │ covering all policy decisions."           │
│                         │ -> Shows 0.0018 / APPROVED (<2ms).                          │ • DEMO-01: Channel fast-path bypass.      │
│                         │ Click `DEMO-03` (100% Balance Drain):                       │ • DEMO-03: Intercepts account takeover.   │
│                         │ -> Shows 0.9981 / DECLINED.                                 │                                           │
├─────────────────────────┼─────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
│ 3. Deep-Dive Inspector  │ In Recent Evaluations table, click "Inspect" on DEMO-03     │ "Our Explanation Engine provides point-   │
│    (30 seconds)         │ Show Radial Operating Risk Score Gauge (0.9981),            │ in-time causal attribution in <1ms with   │
│                         │ Primary Reason Code (RC_EXACT_BALANCE_DRAIN), and           │ zero future data leakage."                │
│                         │ Pre-transaction Causal Evidence Grid.                       │                                           │
├─────────────────────────┼─────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
│ 4. Tamper-Evident Audit │ Top Navigation -> "Tamper-Evident Audit Ledger"             │ "Every decision emits a cryptographically │
│    (15 seconds)         │ Expand the top audit event to reveal SHA-256 block hash     │ chained SHA-256 block with masked PII     │
│                         │ chaining and masked customer account numbers (C123***789).  │ for regulatory non-repudiation."          │
└─────────────────────────┴─────────────────────────────────────────────────────────────┴───────────────────────────────────────────┘
```

---

## 3. All 9 Judge Presets & Oral Defense Table

```
=========================================================================================================================================
PRESET   NAME                          SCENARIO TESTED                             UI ACTION      VIVA ATTACK DEFENSE
=========================================================================================================================================
DEMO-01  Normal Consumer Payment       $84.50 PAYMENT channel purchase             APPROVE        "Fast-track channel bypass avoids model
                                                                                                  latency on 0-fraud payment types."

DEMO-02  Suspicious Severe Outflow     $976k TRANSFER draining 99.37% balance      MANUAL_REVIEW  "Decoupled policy routes borderline risk
                                                                                                  (0.90 <= S < 0.99) to human review instead
                                                                                                  of hard decline, avoiding false-positives."

DEMO-03  Critical Fraud Drain          $284k TRANSFER draining 100% balance        DECLINE        "Immediate automated decline at theta* = 0.990.
                                                                                                  Pre-transaction evidence proves exact drain."

DEMO-04  Benign Cold-Start User        $50.00 TRANSFER from brand new account      APPROVE        "Zero history does not penalize legitimate
                                                                                                  users when balance headroom is healthy."

DEMO-05  State Store Outage Fallback   State store simulated crash                 DECLINE        "Sub-15ms circuit breaker automatically falls
                                                                                   (Fallback)     back to 15-dim Model A causal baseline."

DEMO-06  Tampered Model Boot Check     Checksum verification test                  APPROVE        "ModelManager rejects unverified joblib
                                                                                                  files on boot with ModelIntegrityError."

DEMO-07  Causal Explanation Audit      $99k CASH_OUT liquidation                   DECLINE        "Proves explanation engine generates certified
                                                                                                  narratives strictly from pre-tx features."

DEMO-08  Cryptographic Audit Chaining  Audit trail generation                      APPROVE        "Proves SHA-256 block hash chaining:
                                                                                                  sha256(prev_hash + event_json)."

DEMO-09  Financial Cost Sensitivity    Loss minimization at theta* = 0.990         DECLINE        "Demonstrates financial cost optimization:
                                                                                                  global loss minimum at 0.990 vs theta=0.50."
=========================================================================================================================================
```

---

## 4. Key Reviewer Questions & Model Answers

### Q1: "Why use an operating threshold of 0.990 instead of the standard 0.500?"
> **Answer**: *"In transaction risk with a 0.08% fraud rate, training models with balanced class weights shifts the raw logits (+7.106 shift). A raw score of 0.990 corresponds to ~7.51% calibrated probability. Operating at 0.990 globally minimizes the total financial loss equation ($64k loss vs $12.97M loss at 0.500) while maintaining 96.29% precision and 99.65% recall."*

### Q2: "How do you guarantee zero future data leakage?"
> **Answer**: *"All 36 features in Model B and 15 features in Model A are computable using only state available strictly before transaction execution ($t < \text{execution}$). Post-transaction fields (`newbalanceOrig`, `newbalanceDest`, and `isFlaggedFraud`) are mathematically excluded from both the feature pipeline and explanation evidence."*

### Q3: "What happens if the state store crashes under high load?"
> **Answer**: *"Risk Sentinel incorporates an active sub-15ms Circuit Breaker. If Redis or in-memory state lookup exceeds 15ms or throws an exception, the system automatically degrades to Model A (Causal Baseline), scoring point-in-time features with zero transaction loss and zero 500 errors."*
