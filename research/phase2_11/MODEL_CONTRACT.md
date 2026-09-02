# Risk Sentinel — Machine Learning Model & Lineage Contract
**Document ID**: `MOD-CTR-2.11-001`  
**Status**: `FROZEN MODEL CONTRACT`  
**Model Architecture**: `Scikit-Learn HistGradientBoostingClassifier` | `Balanced Loss`  

---

## 1. Champion & Fallback Model Hierarchy

```
┌────────────────────────────────────────────────────────────────────────┐
│ PRIMARY CHAMPION: Model B — Stateful Causal Behavioral GBDT            │
│  - Features: 36 Dimensions (15 Base + 21 Stateful History & Deviations)│
│  - Artifact: model_b_stateful_hgb.joblib                               │
│  - SHA-256: 5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735 │
│  - Future Test Metrics (Steps 378–743): PR-AUC: 0.9850, F1: 0.9794     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Automatic Circuit Breaker Fallback
                                   │  on State Store >15ms / Error)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ACTIVE FALLBACK: Model A — Causal Point-in-Time Baseline GBDT          │
│  - Features: 15 Dimensions (Point-in-time liquidity & channel only)    │
│  - Artifact: model_a_causal_hgb.joblib                                 │
│  - SHA-256: ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373 │
│  - Future Test Metrics (Steps 378–743): PR-AUC: 0.9843, F1: 0.9794     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Frozen Training & Chronological Splitting Lineage

- **Dataset**: `PS_20174392719_1491204439457_log.csv` ($6,362,620$ total records).
- **Chronological Split Boundaries**:
  - **Train (Steps 1–322)**: $4,433,703$ rows | $3,633$ frauds ($0.0819\%$ base rate). Models were fitted exclusively on this split.
  - **Validation (Steps 323–377)**: $973,173$ rows | $570$ frauds ($0.0586\%$ base rate). Operating threshold ($\theta^* = 0.990$) was selected exclusively on this split.
  - **Held-Out Future Test (Steps 378–743)**: $955,744$ rows | $4,010$ frauds ($0.4196\%$ base rate). Evaluated strictly once for final verification without tuning.

---

## 3. Strict Causal Feature Specification

### Prohibited Fields Invariant (FROZEN #018, #019, #020)
The feature pipeline contains **zero references** to:
- `newbalanceOrig` (Post-transaction sender balance)
- `newbalanceDest` (Post-transaction destination balance)
- `isFlaggedFraud` (Post-hoc heuristic rule flag)
- `orig_gap` / `dest_gap` (Derived post-transaction balance deltas)

### Model A Feature Vector (15 Dimensions)
1. `amount` (Transaction amount)
2. `log_amount` ($\ln(1 + \text{amount})$)
3. `oldbalanceOrg` (Sender balance prior to execution)
4. `oldbalanceDest` (Destination balance prior to execution)
5. `diff_orig_bal_amt` ($\text{oldbalanceOrg} - \text{amount}$)
6. `ratio_orig_bal_amt` ($\frac{\text{oldbalanceOrg}}{\text{amount} + 1}$)
7. `is_orig_zero` ($1$ if $\text{oldbalanceOrg} == 0$ else $0$)
8. `is_dest_zero` ($1$ if $\text{oldbalanceDest} == 0$ else $0$)
9. `hour_of_day` ($\text{step} \pmod{24}$)
10. `day_of_week` ($(\text{step} // 24) \pmod 7$)
11. `is_type_CASH_OUT`
12. `is_type_TRANSFER`
13. `is_type_PAYMENT`
14. `is_type_CASH_IN`
15. `is_type_DEBIT`

### Model B Feature Vector (36 Dimensions = Model A + 21 Extra)
16. `orig_prev_tx_cnt` (Prior transactions by sender)
17. `orig_prev_cum_amt` (Prior cumulative volume by sender)
18. `orig_prev_avg_amt` (Prior average volume by sender)
19. `orig_prev_max_amt` (Prior max volume by sender)
20. `orig_time_since_prev` (Step elapsed since sender last transaction)
21. `orig_unique_dest_cnt` (Number of unique recipients sent to)
22. `orig_prev_transfer_cnt` (Prior TRANSFER transactions)
23. `orig_prev_cash_out_cnt` (Prior CASH_OUT transactions)
24. `dest_prev_in_tx_cnt` (Prior incoming transactions to recipient)
25. `dest_prev_in_cum_amt` (Prior cumulative incoming volume)
26. `dest_prev_in_avg_amt` (Prior average incoming volume)
27. `dest_prev_in_max_amt` (Prior max incoming volume)
28. `dest_time_since_prev` (Step elapsed since recipient last received)
29. `dest_unique_orig_cnt` (Number of unique senders received from)
30. `pair_prev_tx_cnt` (Prior transactions between this sender and destination)
31. `pair_time_since_prev` (Step elapsed since last sender-dest interaction)
32. `is_sender_cold_start` ($1$ if $\text{orig\_prev\_tx\_cnt} == 0$ else $0$)
33. `is_dest_cold_start` ($1$ if $\text{dest\_prev\_in\_tx\_cnt} == 0$ else $0$)
34. `is_pair_novel` ($1$ if $\text{pair\_prev\_tx\_cnt} == 0$ else $0$)
35. `orig_amt_vs_avg_ratio` ($\frac{\text{amount}}{\text{orig\_prev\_avg\_amt} + 1}$)
36. `orig_amt_vs_max_diff` ($\text{amount} - \text{orig\_prev\_max\_amt}$)

---

## 4. State Lifecycle & Cold-Start Contract

1. **Read-Before-Compute / Write-After-Decision**:
   - For transaction $t$, state is read strictly before computing features: $\text{History}(t) = \{\tau < t\}$.
   - State counters are incremented strictly post-decision.
2. **Cold-Start Non-Prejudice (FROZEN #010)**:
   - When $\text{is\_sender\_cold\_start} == 1$, historical velocity counters default to $0.0$, and the transaction is scored purely on point-in-time liquidity dynamics without automatic fraud bias.
