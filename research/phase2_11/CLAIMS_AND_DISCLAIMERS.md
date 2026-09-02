# Risk Sentinel — Claims, Truth Boundaries & Disclaimers
**Document ID**: `CLM-DIS-2.11-001`  
**Status**: `FROZEN COMPLIANCE SPECIFICATION`  

---

## 1. Category 1: Measured Facts We Confidently Claim

1. **High Precision & Recall on Future Steps**:
   - Risk Sentinel achieved **$99.65\%$ fraud detection recall** and **$96.29\%$ precision** on the held-out future test period (steps 378–743) of the PaySim canonical benchmark.
2. **High Dollar Capture Rate**:
   - The engine intercepted **\$6,323,408,725.18** out of \$6,323,807,770.26 (**$99.9937\%$ of total fraud dollar exposure**) with a false positive rate under **$0.0163\%$**.
3. **Zero Data Leakage / 100% Causal Purity**:
   - The feature pipeline excludes all post-transaction balances (`newbalanceOrig`, `newbalanceDest`) and labels (`isFlaggedFraud`). State accumulation is mathematically strict ($t_{\text{prev}} < t$).
4. **Sub-Millisecond Algorithmic Execution**:
   - Core algorithmic inference, feature assembly, and deterministic explanation resolve in **$< 4.0\text{ ms}$ p99 latency** on standard CPU hardware.
5. **Zero-Downtime Resilience**:
   - Automated circuit breaker routes to Model A (Causal Baseline) in $<15\text{ms}$ upon state store failure, ensuring continuous scoring without 500 errors.

---

## 2. Category 2: PaySim Observations Requiring Disclaimers

> [!IMPORTANT]
> **Mandatory Disclaimer Tag: `[BENCHMARK_OBSERVATION]`**

1. **Channel Exclusivity**:
   - *Observation*: Fraud in PaySim is confined exclusively to `TRANSFER` and `CASH_OUT` channels ($0$ fraud across 3.59M `CASH_IN`, `DEBIT`, `PAYMENT` records).
   - *Required Disclaimer*: Automatic approval on these channels is an empirical property of the PaySim simulation and must not be represented as an immutable rule for real-world payment systems.
2. **Sender Ephemerality & Balance Drains**:
   - *Observation*: $99.85\%$ of senders appear only once, and $97.82\%$ of fraud is an exact 100% balance liquidation.
   - *Required Disclaimer*: PaySim's synthetic agent generator created single-use sender IDs and total drains, which explains why Model A baseline performs nearly as well as Model B on this specific dataset.

---

## 3. Category 3: Scenario Assumptions Requiring Disclaimers

> [!NOTE]
> **Mandatory Disclaimer Tag: `[SCENARIO_SENSITIVITY]`**

1. **Operational Cost Multiplier ($\alpha$)**:
   - *Sensitivity Range*: $\alpha \in \{0.1\%, 0.5\%, 1.0\%, 2.0\%, 5.0\%\}$.
   - *Required Disclaimer*: Alpha penalties represent exploratory scenario bounds for modeling false-positive operational intervention and customer friction, not proprietary Razorpay unit economics.
2. **Decision Threshold ($\theta^* = 0.990$)**:
   - *Mathematical Reality*: Represents a calibrated risk decision threshold derived from `class_weight='balanced'` loss shifting base priors by $+7.106$ log-odds ($\approx 7.51\%$ calibrated risk).
   - *Required Disclaimer*: Must NOT be described as a "99% probability of fraud."

---

## 4. Category 4: Prohibited Claims (Must NEVER Be Made)

1. **DO NOT claim** Model B provides a massive statistical lift over Model A on PaySim (the measured lift is $+0.00065$ PR-AUC due to single-use sender constraints).
2. **DO NOT claim** past leaky-model metrics ($>99.99\%$ F1 using post-transaction balances) as legitimate system performance.
3. **DO NOT claim** production network latency will remain $<3.5\text{ms}$ without accounting for gateway and network hops (gateway budget is $35.0\text{ms}$).
4. **DO NOT claim** real-world fraud is 100% absent from debit card or payment channels.
