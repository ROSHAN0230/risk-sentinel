# Risk Sentinel — Judge Attack Defense Guide (42 Technical Q&As)
**Document ID**: `QA-JUDGE-DEFENSE-001`  
**Date**: `2026-09-02`  
**Target Competition**: `Razorpay AI Buildathon 2026` — `Track 02: AI Risk Manager`  
**Standard**: Short, precise, mathematically grounded, evidence-backed, strictly defense-only.

---

### 1. What exact Track-02 loss does Risk Sentinel address?
**Answer**: Catastrophic liquidity drainage and account takeover (ATO) fraud occurring through peer transfers and cash-out channels.

### 2. What makes this a "working" detector?
**Answer**: It is not a Jupyter notebook or mock UI. It is an end-to-end executable system with serialized GBDT models, sub-3ms inference, a decoupled policy engine, a REST API, an immutable audit ledger, a live investigation workspace, and automated regression suites.

### 3. Where is the held-out test set?
**Answer**: Steps 378–743 of the standardized PaySim benchmark (955,744 transactions, 4,010 ground-truth frauds). It was strictly quarantined during model training (Steps 0–335) and validation tuning (Steps 336–377).

### 4. Why PaySim?
**Answer**: PaySim is the standard, public, reproducible academic benchmark for high-volume, severe-imbalance financial fraud (0.42% prevalence across 6.36 million records).

### 5. Is PaySim representative of Razorpay?
**Answer**: No. PaySim models synthetic mobile money transfers, not Razorpay's proprietary merchant stream, card payments, or UPI flows. We use it as our statistical evaluation baseline, while our Razorpay Webhook Adapter demonstrates real gateway integration.

### 6. What exactly do precision and recall measure here?
**Answer**: Precision measures the percentage of flagged transactions that were genuine fraud (96.29%), guarding against merchant friction. Recall measures the percentage of all fraud attacks successfully intercepted (99.65%).

### 7. Why is recall 99.65%?
**Answer**: Out of 4,010 ground-truth frauds in the held-out test set, the model successfully intercepted 3,996 ($\frac{3996}{4010} = 99.65\%$).

### 8. Why are there 154 false positives?
**Answer**: 154 legitimate transactions exhibited high-proportion liquidity transfers resembling account drains. Across 951,734 legitimate transactions, this represents a false-positive rate of just 0.0162%.

### 9. Why are there 14 false negatives?
**Answer**: Exactly 14 frauds were missed because the perpetrators performed partial transfers, leaving substantial liquidity in the sender account. At threshold $\theta^*=0.990$, these stayed below the decline boundary to prevent thousands of legitimate false alarms.

### 10. What is the dollar impact of those false negatives?
**Answer**: The 14 missed frauds represented \$399,045.08 out of \$6.32B total fraud volume—a loss exposure of only 0.0063%.

### 11. What does 99.9937% dollar interception mean?
**Answer**: Out of \$6,323,807,770.26 in total fraud attempted in the held-out test set, the system intercepted \$6,323,408,725.18.

### 12. Is that a Razorpay loss figure?
**Answer**: No. It is the historical fraud volume within the PaySim academic benchmark. It does not represent Razorpay internal financial losses.

### 13. Can Risk Sentinel currently block a live Razorpay transaction?
**Answer**: No. Risk Sentinel currently demonstrates Razorpay-compatible Test Mode webhook ingestion and risk evaluation. Production live payment interception is not claimed.

### 14. What does the Razorpay webhook integration actually prove?
**Answer**: It proves external interoperability: verifying HMAC-SHA256 signatures, enforcing event idempotency, honest zero-fabrication gating, and evaluating risk through the production engine.

### 15. Is the webhook actually delivered by Razorpay or merely Razorpay-compatible?
**Answer**: It accepts Razorpay-compatible webhook payloads formatted identically to Razorpay's API standard in Test Mode. We do not claim an active production merchant contract with Razorpay.

### 16. What happens when webhook data is insufficient?
**Answer**: The adapter halts evaluation and emits `INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION`, listing the missing pre-transaction balance fields.

### 17. Why is zero-fabrication gating important?
**Answer**: Naive AI demos invent fake account balances when fields are missing. In financial risk, fabricating inputs produces hallucinated scores. We refuse to score until true balance context is supplied.

### 18. Why Model B instead of Model A?
**Answer**: Model A is a 15-feature point-in-time model. Model B adds 21 stateful features tracking destination mule fan-in velocity and sender history. Model A serves as an instant fallback when caches fail.

### 19. Why is Model B's measured lift modest?
**Answer**: On PaySim, Model B improved PR-AUC by +0.00065. PaySim accounts are highly ephemeral (most transacting only once), so historical velocity has limited signal on this specific dataset. Model B's primary value is structural defense in real enterprise environments.

### 20. What happens during cold start?
**Answer**: Unseen accounts transacting normal amounts clear automatically via fast-path (`APPROVE`, score 0.0018). But an unseen account attempting an immediate 100% balance drain is caught by point-in-time drain ratios (`DECLINE`, score 0.9981).

### 21. What happens if behavioral state is unavailable?
**Answer**: The state store circuit breaker trips after 15ms or on error, automatically falling back to Model A in 1.1ms. The transaction is scored safely without gateway downtime.

### 22. Is 0.990 a probability?
**Answer**: No. 0.990 is a decision operating threshold chosen on validation data under class reweighting. It is an operational risk score, not a calibrated probability.

### 23. Why 0.990?
**Answer**: On 973,173 validation transactions, $\theta^*=0.990$ was empirically validated as the lowest-cost operating point across all tested merchant friction values ($\alpha \in [0.001, 0.050]$), maintaining 0 validation false negatives.

### 24. How was the threshold selected?
**Answer**: Through grid evaluation across 15 candidate thresholds strictly on the validation split (Steps 336–377).

### 25. Was the held-out test set used to tune the threshold?
**Answer**: Never. The held-out test set (Steps 378–743) was completely quarantined and evaluated only once after the threshold was permanently frozen.

### 26. What does the economics simulator actually optimize?
**Answer**: It models $\text{Total Cost} = \text{Missed Fraud FN Dollars} + \alpha \times \text{Flagged Non-Fraud Volume}$, allowing merchants to explore sensitivity to false-positive friction.

### 27. Is alpha a Razorpay business parameter?
**Answer**: No. $\alpha$ is an exploratory simulation parameter (0.1% to 5.0%) modeling customer challenge friction. It does not reflect Razorpay internal unit economics.

### 28. Can the economics simulator modify production policy?
**Answer**: No. The simulator is strictly a read-only scenario modeling tool. Production threshold remains cryptographically locked at $\theta^*=0.990$.

### 29. How are explanations generated?
**Answer**: Deterministically via `ExplanationResolver`. Model decision boundaries and causal feature ratios map to 8 certified Reason Codes in <0.85ms without using generative LLMs.

### 30. Can the LLM hallucinate a fraud reason?
**Answer**: No generative LLM is used in the decision path. All narratives are deterministic rule templates parameterized by actual transaction features.

### 31. How is the audit trail protected?
**Answer**: Every decision is appended to a tamper-evident SHA-256 block chain where each block incorporates the hash of the preceding block and decision payload.

### 32. What information is stored in the audit trail?
**Answer**: Event ID, timestamp, transaction ID, masked account IDs, input snapshots, extracted causal features, model version, policy version, operating threshold, and chained block hash.

### 33. How is PII handled?
**Answer**: Account numbers are masked at ingestion (e.g., `C123456789` $\to$ `C123***789`). Full account numbers are never written to plain-text audit ledgers.

### 34. Can an investigation GET request trigger a new model decision?
**Answer**: No. Investigation endpoints are strictly read-only and observational. They query historical memory buffers and perform zero inference or state mutation.

### 35. What is DEMO_FIXTURE provenance?
**Answer**: Pre-computed reference transactions (DEMO-01 to DEMO-09) labeled with purple badges to allow judges to explore edge cases deterministically without live traffic dependencies.

### 36. What is RAZORPAY_TEST_MODE provenance?
**Answer**: Webhook events received via `POST /v1/webhooks/razorpay` in Test Mode. Distinctly labeled with amber badges.

### 37. What is RESEARCH_BENCHMARK provenance?
**Answer**: Historical performance metrics derived from the held-out PaySim test split, clearly segregated from live engine telemetry.

### 38. What does "real-time" mean in this project?
**Answer**: Synchronous in-memory execution of feature extraction, model inference, explanation resolution, policy decision, and audit hashing within <3.0ms per request.

### 39. What latency has actually been measured?
**Answer**: Local single-process latency: p50 = 1.15ms, p95 = 2.52ms, p99 = 3.15ms across 1,000 stress-test transactions.

### 40. What does the internal 35 ms engineering budget mean?
**Answer**: It is an internal performance design target representing the maximum allowable processing window for a risk sidecar in high-speed payment architectures.

### 41. What claims are intentionally NOT being made?
**Answer**: We do NOT claim live production interception, calibrated probabilities, causal counterfactual proofs, direct generalization of PaySim metrics to Razorpay, or proprietary Razorpay unit economics.

### 42. What would be required before production deployment?
**Answer**: Distributed Redis cluster replacing in-memory state stores, Kafka/event streaming for webhook queuing, retraining on proprietary Razorpay merchant datasets, and shadow-mode A/B testing against live payment flows.
