# Risk Sentinel — Technical Judge Attack Test & Defense Handbook
**Document ID**: `VIVA-DEFENSE-2.8-001`  
**Status**: `FROZEN VIVA & PITCH DEFENSE GUIDE`  

---

### Q1: "Your operating threshold is 0.99. Does that mean the model is saying there is a 99% probability of fraud?"
**Defense Answer**:  
**No, absolutely not.** That is a common misunderstanding of balanced-loss gradient boosting. Because fraud prevalence in training is extremely rare ($0.0819\%$, or 1 fraud per 1,220 legitimate transactions), we trained our tree ensemble with `class_weight='balanced'`. This re-weights positive fraud loss by $1,219.4\times$, shifting the baseline prior log-odds by $\ln(1219.4) \approx +7.106$.  
Mathematically, an uncalibrated output score of $0.99$ translates to a true calibrated Bayesian posterior fraud probability of:
$$P_{\text{true}}(\text{Fraud}) = \sigma\left(\ln\left(\frac{0.99}{0.01}\right) - 7.106\right) = \sigma(4.595 - 7.106) = \sigma(-2.511) \approx \mathbf{7.51\%}$$
Therefore, a score of $0.99$ represents an **operating decision threshold** identifying high-leverage risk events (where fraud likelihood is elevated $>90\times$ above the baseline prior), not a calibrated literal 99% probability statement.

---

### Q2: "Why did you select 0.99 rather than the standard 0.50 threshold?"
**Defense Answer**:  
Selecting threshold 0.50 on class-imbalanced data trained with balanced weighting is a critical error. At $\theta = 0.50$ on validation data, the model flags $6,644$ non-fraud transactions (FPR $= 0.68\%$, Precision $= 7.91\%$), causing massive false declines and operational cost (\$12.97M).  
We ran a rigorous, continuous threshold sweep on validation data ($0.01 \le \theta \le 0.999$) under financial cost optimization ($\text{Cost} = \text{FN Dollars Missed} + 1.0\% \times \text{FP Dollars Flagged}$). $\theta^* = 0.99$ achieved the global minimum financial loss (\$64,345.47) while intercepting $100.00\%$ of fraud volume on validation data.

---

### Q3: "What happens if your Redis or state store goes down in production?"
**Defense Answer**:  
The system executes a **graceful degradation circuit breaker** with zero downtime. If the state store is unreachable or lookup latency exceeds the 15ms SLA threshold, the engine immediately switches to **Model A (Causal Baseline)**. Model A relies strictly on point-in-time features (`diff_orig_bal_amt`, `oldbalanceOrg`, `amount`, `type`) and requires zero stateful cache lookups. On our held-out future test, Model A achieves $96.29\%$ precision and $99.65\%$ recall, ensuring continuous protection without blocking transactions.

---

### Q4: "How can you prove you didn't leak future or post-transaction data into your features?"
**Defense Answer**:  
We implemented and executed four automated cryptographic and structural audit gates in `research/phase2_6/leakage_audit.py` and `research/phase2_7/audit.py`:
1. **Prohibited Field Verification**: Confirmed zero references to `newbalanceOrig`, `newbalanceDest`, `isFlaggedFraud`, or derived balance deltas.
2. **Chronological Monotonicity**: Verified step timestamps are monotonically non-decreasing ($1 \le \text{step} \le 743$).
3. **Point-in-Time Historical Replay Assertions**: Sampled 250 random transactions across 6.36M rows and asserted that the sequentially computed state bitwise matched a strictly past-sliced recomputation ($\{j < i\}$). Discrepancies = **0**.
4. **Future Invariance Check**: Truncated future data slices and proved that past feature arrays were bitwise identical, confirming zero lookahead dependency.

---

### Q5: "Model B (Stateful) achieved PR-AUC 0.98496 while Model A achieved 0.98431 on future test — a lift of only 0.065 percentage points. Why bother keeping Model B?"
**Defense Answer**:  
This is one of the most critical scientific insights from our Phase 2.7 forensics:
In PaySim, **$99.85\%$ of senders appear only once** (synthetic ephemeral IDs; zero repeat fraud senders). Furthermore, $97.82\%$ of fraud is an exact 100% single-step balance liquidation. Because PaySim's synthetic generator did not create multi-step sender fraud histories, Model A's point-in-time liquidity features capture the signal almost completely.  
However, in real-world payment ecosystems (e.g. Razorpay/UPI), adversaries operate across velocity bursts, account takeovers, and mule aggregation rings. Keeping Model B provides the **mandatory stateful engineering architecture** (entity velocity, cold-start indicators, deviation ratios) required for production reality, while Model A serves as an ultra-fast fallback.

---

### Q6: "If PaySim has synthetic shortcuts like single-use senders and 100% balance drains, why did you use it?"
**Defense Answer**:  
PaySim is the canonical, publicly verifiable, and peer-reviewed benchmark dataset for financial transaction fraud research. Rather than hiding its synthetic limitations, we conducted dataset forensics (Phase 2.6/2.7), proved that past near-perfect academic results were caused by post-transaction balance leakage (`newbalanceOrig`), isolated the causal point-in-time features, and explicitly documented PaySim's structural shortcuts in our risk taxonomy. This proves our system's scientific honesty and adherence to rigorous ML auditing.

---

### Q7: "Why should a compliance officer or judge trust your explanations? Are they just hallucinated text?"
**Defense Answer**:  
Our explanations are **deterministic causal attributions**, not LLM hallucinations or expensive approximate SHAP samplers. The explanation engine inspects the actual feature split contributions in the decision tree, evaluates the exact numerical deltas (e.g., $\text{Amount} = \$181,954.34$ draining $100\%$ of $\text{Balance} = \$181,954.34$ on a TRANSFER channel to a zero-balance destination), and maps them to certified regulatory **Reason Codes** (`RC_EXACT_BALANCE_DRAIN`, `RC_HIGH_RISK_CHANNEL_COMBO`). Every reason code contains exact mathematical evidence stored directly in the immutable audit log.

---

### Q8: "How does your system handle cold-start accounts? Does 'no history' mean automatic fraud?"
**Defense Answer**:  
**No. Under FROZEN Rule #010, cold-start is treated as contextual risk information, never automatic evidence of fraud.**  
In our feature architecture, `is_sender_cold_start` and `is_dest_cold_start` are explicit binary flags, and prior velocity counters default to neutral baselines ($0.0$). On our held-out future test, out of 953,221 sender cold-start transactions, the model approved **$949,069$ legitimate cold-start transactions without interruption (FPR $= 0.016\%$)**, while precisely isolating the $3,984$ fraudulent drains.

---

### Q9: "Can a model failure or crash cause legitimate customer transactions to be blocked?"
**Defense Answer**:  
No. The engine implements a strict **fail-safe degradation ladder**:
1. If Model B inference crashes or throws a numerical exception $\to$ fallback immediately to Model A.
2. If Model A also crashes $\to$ evaluate deterministic fail-safe schema rules.
3. If gateway deadline (35ms) is reached $\to$ merchant policy determines whether to trigger a non-destructive step-up challenge (SMS/OTP) or approve with a deferred review flag. Legitimate users are never silently hard-declined on system failure.

---

### Q10: "Can your audit trail deterministically reproduce a historical decision during a regulatory audit?"
**Defense Answer**:  
**Yes, 100% deterministically.** Every decision audit event records:
- The exact input payload snapshot and raw extracted feature vector.
- The SHA-256 hash of the frozen model artifact.
- The active policy rule ID and threshold version.  
Feeding the logged feature vector back into the SHA-256 verified model artifact yields the identical raw risk score, band, action, and reason codes.

---

### Q11: "What prevents a malicious client or compromised frontend from bypassing or spoofing risk scores?"
**Defense Answer**:  
Under our **Security Architecture (Trust Boundary 1 & 2)**:
The frontend client has zero influence over risk scoring. The client transmits only transaction metadata to the edge API Gateway. All state lookups, causal feature extraction, ML inference, and policy evaluations execute exclusively in an isolated, private backend VPC. The frontend cannot inject scores, bypass tiers, or alter reason codes.

---

### Q12: "Why didn't you use Deep Learning (LSTM, Transformers, or Graph Neural Networks)?"
**Defense Answer**:  
For tabular payment fraud with tabular point-in-time liquidity dynamics, tree-based gradient boosting (specifically `HistGradientBoosting` / LightGBM) consistently outperforms deep neural networks in both tabular benchmark accuracy and inference latency. Our GBDT evaluates inference in $< 4.5\text{ms}$ on standard CPU cores without GPU dependencies, whereas GNNs or large sequential LSTMs introduce significant latency ($>50\text{ms}$), cold-start graph sparsity issues, and non-deterministic inference jitter.

---

### Q13: "Why did you use a chronological train/val/test split instead of standard 5-fold stratified cross-validation?"
**Defense Answer**:  
Random k-fold cross-validation or random train-test splitting on time-series transaction logs is a **fatal methodological error (Temporal Leakage)**. In fraud detection, future fraudsters adapt to past defense mechanisms. Shuffling transactions allows the model to learn from "future" entity interactions to predict the "past," artificially inflating test metrics. Our chronological split (Train: steps 1–322, Val: steps 323–377, Future Test: steps 378–743) strictly simulates real-world deployment over time.

---

### Q14: "If 97.8% of fraud is exact balance drain, why not just write a simple `if oldbalanceOrg == amount: decline()` rule instead of machine learning?"
**Defense Answer**:  
Writing a static heuristic rule creates catastrophic operational blindness:
1. Legitimate users frequently close or zero out accounts (there are legitimate full drains in payments).
2. Fraudsters immediately evade static rules by leaving \$1.00 or draining in 95% tranches.
3. Our GBDT model evaluates multi-dimensional non-linear interactions across amount scale, liquidity ratio, transaction channel, hour of day, and destination mule aggregation simultaneously, capturing both exact drains and non-exact evasive transactions without brittle manual rule maintenance.

---

### Q15: "How does your system handle extreme temporal distribution shifts in production?"
**Defense Answer**:  
Our Phase 2.6 and 2.7 benchmarks proved resilience against severe distribution shifts:
In our dataset, fraud prevalence shifted by **$5.1\times$** from the training period ($0.0819\%$) to the future test period ($0.4196\%$). Despite this massive density surge, our frozen model and threshold achieved **$99.65\%$ recall, $96.29\%$ precision, and intercepted $99.99\%$ of fraud dollars** on the future test without retraining, proving that our causal features capture invariant fraud physics rather than temporal artifacts.

---

### Q16: "What is the single biggest remaining risk in your system?"
**Defense Answer**:  
The primary residual risk is **adversarial micro-drain evasion** (an attacker intentionally breaking a large balance drain into small, distributed transactions over days). While our destination stateful counters (`dest_prev_in_tx_cnt`, `dest_unique_orig_cnt`) detect the receiving mule account, an attacker using multi-hop distributed networks across long timeframes requires persistent graph clustering. In Phase 2.9+, we recommend augmenting the stateful layer with persistent destination velocity clustering in the background.
