# Risk Sentinel — 5-Minute Competition Demo Script
**Document ID**: `SCRIPT-DEMO-5MIN-001`  
**Date**: `2026-09-02`  
**Target Competition**: `Razorpay AI Buildathon 2026` — `Track 02: AI Risk Manager`  
**Timing**: Strict 5-Minute Execution (300 Seconds Total)  

---

### [0:00 – 0:30] Screen: Executive Dashboard (`/dashboard`)
#### Problem Statement & Track-02 Mission
- **Presenter Action**: Open browser to `http://127.0.0.1:8000/`. Highlight the executive KPI strip.
- **Verbal Delivery**:
  > *"Judges, in Indian digital payments, AI-enabled account takeovers and sudden liquidity drains silently erode merchant trust and capital. For Track 02, we built Risk Sentinel: a working, sub-3-millisecond causal risk decision engine that stops fraud while explicitly accounting for false-positive merchant friction.*
  > *Notice our permanent disclaimer immediately: we do not claim uncalibrated 99% probabilities or proprietary Razorpay production KPIs. We present verified, held-out empirical benchmark evidence."*

---

### [0:30 – 1:15] Screen: Live Stream & Demo Console (`/stream`)
#### Live Risk Evaluation & Fast-Path Bypass
- **Presenter Action**: Click **Live Stream & Demo** in Navbar. Click the **DEMO-04 (Benign Cold-Start Account)** preset button.
- **Verbal Delivery**:
  > *"Let’s observe real-time evaluation. Here is a brand new account making a standard transfer. Because the transaction exhibits adequate balance headroom and benign velocity, Risk Sentinel evaluates it in 1.1 milliseconds and clears it instantly: `APPROVED` with an operating risk score of 0.0018.*
  > *Notice that benign channels like standard merchant payments bypass heavy scoring entirely, guaranteeing zero added latency for legitimate commerce."*

---

### [1:15 – 2:00] Screen: Live Stream (`/stream`)
#### High-Risk Interception & Deterministic Explanation
- **Presenter Action**: Click **DEMO-03 (Critical Balance Drain)** preset button. Highlight the red decline card.
- **Verbal Delivery**:
  > *"Now, watch an active attack: a critical account takeover where a fraudster attempts an exact 100% liquidation of \$284,100. In 1.4 milliseconds, the engine intercepts the transaction: `DECLINED`.*
  > *Crucially, we do not use an opaque black box or a generative LLM that can hallucinate. Our deterministic explanation resolver instantly certifies primary reason code `RC_EXACT_BALANCE_DRAIN` with point-in-time causal evidence proving the exact balance liquidation."*

---

### [2:00 – 2:45] Screen: Investigation Workspace (`/inspector`)
#### 9-Pillar Dossier & Deterministic SOP Protocol
- **Presenter Action**: Click **Inspect** on DEMO-03, or switch to **Investigation Workspace** in Navbar.
- **Verbal Delivery**:
  > *"This brings us into our core Track-02 capability: the Investigation Workspace. When a transaction is declined, a human risk officer or merchant needs immediate, actionable answers without guesswork.*
  > *On the left is our unified Investigation Queue with explicit provenance badges: Audit Record, Test Mode, and Demo Fixture. On the right is the complete 9-pillar dossier.*
  > *Look at the Standard Operating Procedure guidance: it provides a deterministic review checklist tailored to the exact reason code—instructing the analyst to initiate out-of-band verification and place a provisional freeze on the destination account.*
  > *At the bottom is the SHA-256 block hash, proving that the decision was cryptographically logged to our immutable regulatory audit ledger."*

---

### [2:45 – 3:30] Screen: Live Stream (`/stream`)
#### Razorpay-Compatible Test Mode Webhook Integration
- **Presenter Action**: Scroll down to the **Razorpay Test Mode Webhook Monitor**. Click **Dispatch Raw Event**, then click **Dispatch Enriched Drain**.
- **Verbal Delivery**:
  > *"Next, we demonstrate external gateway interoperability via our native Razorpay Webhook Adapter. When an external payment event arrives at `/v1/webhooks/razorpay`, we verify its HMAC-SHA256 signature and check idempotency.*
  > *Notice our zero-fabrication gating: when a raw gateway payload arrives without banking balance context, Risk Sentinel refuses to invent fake data—it marks the event `INSUFFICIENT_FEATURES`.*
  > *When pre-transaction balance context is enriched in Test Mode, the engine evaluates it through our full GBDT pipeline and intercepts the fraud with score 0.9981."*

---

### [3:30 – 4:15] Screen: Research Forensics & Economics (`/benchmarks`)
#### False-Positive Cost Simulator & Alpha Sensitivity
- **Presenter Action**: Click **Research Forensics** in Navbar. Adjust the **Intervention Friction Factor ($\alpha$)** slider from 0.1% to 1.0% to 5.0%.
- **Verbal Delivery**:
  > *"The Track 02 bar specifically demands honest metrics including false-positive cost. We built an interactive Decision Economics Simulator across 15 empirical thresholds evaluated on 973,173 validation transactions.*
  > *Here, $\alpha$ represents the business friction cost per dollar challenged. As we slide $\alpha$ across the entire range from 0.1% to 5.0%, notice that our locked operating threshold $\theta^*=0.990$ consistently achieves the lowest scenario cost while maintaining zero missed frauds on validation data.*
  > *And notice our banner: this is strictly an analytical simulation. Production policy remains locked."*

---

### [4:15 – 4:45] Screen: Research Forensics (`/benchmarks`)
#### Held-Out Benchmark Truth (Steps 378–743)
- **Presenter Action**: Scroll down to the **Future Held-Out PaySim Benchmark Evaluation** section.
- **Verbal Delivery**:
  > *"Finally, we present our held-out test evidence: 955,744 transactions across Steps 378 to 743, strictly quarantined until after threshold selection.*
  > *Here are our verified metrics:*
  > *- 96.29% Precision*
  > *- 99.65% Recall — capturing 3,996 of 4,010 ground-truth frauds with only 14 false negatives.*
  > *- Out of \$6.32 billion in total attempted fraud, Risk Sentinel intercepted \$6,323,408,725.18, achieving 99.9937% dollar interception.*
  > *Every single dollar is historical PaySim benchmark volume—honestly reported without inflated live claims."*

---

### [4:45 – 5:00] Closing Statement
#### Defense-Only Conclusion
- **Verbal Delivery**:
  > *"To summarize: We didn't build an ungrounded LLM chatbot or optimize for superficial demo tricks. We built a defensible, production-hardened risk manager with measured precision, honest false-positive economics, deterministic explanations, and a complete investigation workflow.*
  > *Risk Sentinel is frozen, tested, and ready for your questions. Thank you."*
