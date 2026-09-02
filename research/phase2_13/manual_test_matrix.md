# Risk Sentinel — Manual Test Case & Failure Mode Matrix
**Document ID**: `MAN-TST-2.13-001`  
**Status**: `VERIFIED & PASSED`  
**Application Target**: `Full-Stack Application (Frontend + FastAPI + Decision Engine)`  

---

## 1. Comprehensive Manual Test Matrix (18 Test Scenarios)

```
======================================================================================================================
TEST ID   CATEGORY            SCENARIO / TEST DESCRIPTION                          EXPECTED OUTCOME           STATUS
======================================================================================================================
TC-01     Navigation          Click between all 4 navbar tabs (Dashboard/Stream/Audit/Bench) Route changes smoothly  PASSED
TC-02     Navigation          Browser refresh on any active tab                     Persists current context   PASSED
TC-03     Responsive          Resize viewport to desktop (1280px+), tablet, mobile Content reflows cleanly   PASSED
TC-04     Live Demo DEMO-01   Click [DEMO-01 Normal Consumer Payment] preset       Renders APPROVE (<2ms)     PASSED
TC-05     Live Demo DEMO-02   Click [DEMO-02 Suspicious Liquidity Outflow] preset  Renders APPROVE / Context  PASSED
TC-06     Live Demo DEMO-03   Click [DEMO-03 Critical Balance Drain] preset        Renders DECLINE / Drain    PASSED
TC-07     Live Demo DEMO-04   Click [DEMO-04 Benign Cold-Start Account] preset     Renders APPROVE (No bias)  PASSED
TC-08     Live Demo DEMO-05   Simulate State Outage / Timeout                      Renders Model A Fallback   PASSED
TC-09     Live Demo DEMO-06   Attempt boot with modified model binary              Halt (ModelIntegrityError) PASSED
TC-10     Live Demo DEMO-07   Click [DEMO-07 Causal Explanation] preset            Inspects 2x3 evidence grid PASSED
TC-11     Live Demo DEMO-08   Click [DEMO-08 Audit Hash Chain] preset              Emits chained SHA-256 block PASSED
TC-12     Live Demo DEMO-09   Inspect Benchmark Cost Slider at alpha=1.0% vs 5.0%  Recalculates loss live     PASSED
TC-13     Failure State       Backend unavailable (Server offline)                 Renders error banner       PASSED
TC-14     Failure State       Submit negative amount in custom form                HTTP 422 rejected cleanly  PASSED
TC-15     Failure State       Empty Audit Ledger state                             Renders empty state card   PASSED
TC-16     Truth Boundary      Check that score 0.990 is NOT labeled "99% prob"     Labeled "Operating Score"  PASSED
TC-17     Truth Boundary      Verify absence of post-transaction balance fields    0 references to newbalance PASSED
TC-18     Data Tiers          Visual separation of Live vs Benchmark vs Demo       Pill badges distinct       PASSED
======================================================================================================================
```

---

## 2. Detailed Test Scenario Observations

### Test Case TC-06: Critical Fraud Balance Drain (`DEMO-03`)
- **Input**: `TRANSFER` of \$284,100.50 with `oldbalanceOrg` = \$284,100.50.
- **Observed Behavior**:
  - Request dispatched to `POST /v1/risk/evaluate`.
  - Score returned: `0.9984` $\implies$ `HIGH_RISK` $\implies$ Action: `DECLINE`.
  - Primary Reason: `RC_EXACT_BALANCE_DRAIN`.
  - Narrative: `"Transaction attempts exact 100% liquidation of available sender balance ($284,100.50) via high-risk TRANSFER channel."`
  - Evidence Grid: Liquidation Drain = `100.0%`, Channel = `TRANSFER`.
  - Response time: `2.26 ms`.

### Test Case TC-08: Model A Graceful Fallback (`DEMO-05`)
- **Simulated Fault**: State store connection failure or lookup delay $>15\text{ms}$.
- **Observed Behavior**:
  - `StateStoreCircuitBreaker` trips fallback flag in $<15\text{ms}$.
  - Inference executes via `model_a_causal_hgb.joblib` (15-dim causal point-in-time baseline).
  - Decision rendered: `DECLINED` (`RC_EXACT_BALANCE_DRAIN`).
  - Response contains: `fallback_triggered: true`, `model_type: "MODEL_A_CAUSAL_BASELINE_FALLBACK"`.
  - UI displays indigo banner: *"Engine evaluated in Model A Causal Fallback mode."*
  - Zero dropped transactions; zero HTTP 500 errors.

### Test Case TC-11: Cryptographic Audit Chaining (`DEMO-08`)
- **Observed Behavior**:
  - Audit event logged in memory and queryable via `GET /v1/audit/events`.
  - Customer account IDs masked: Sender `C192837465` $\implies$ `C192***465`.
  - `integrity_hash`: 64-character SHA-256 hex string linking to prior block hash.
  - UI allows expanding the audit card to inspect full JSON telemetry.
