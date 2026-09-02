# Risk Sentinel — P1.2 Implementation Gap Audit: Investigation Workspace
**Document ID**: `AUDIT-P1.2-GAP-001`  
**Date**: `2026-09-02`  
**Phase**: `Phase P1.2 — Investigation Workspace`  
**Track Alignment**: `Razorpay AI Buildathon — Track 02: AI Risk Manager`  
**Audit Scope**: `Read-Only Reconnaissance & Architectural Plan`  
**Implementation Status**: **`IMPLEMENTATION NOT STARTED (AUDIT ONLY)`**  

---

## 1. Executive Summary

Phase P1.2 focuses on closing the operational loop for Track 02:
$$\text{Observe} \longrightarrow \text{Detect} \longrightarrow \text{Explain} \longrightarrow \text{Investigate} \longrightarrow \text{Decide} \longrightarrow \text{Record}$$

A risk detection engine is only as good as the speed and defensibility with which a human risk analyst, merchant, or judge can interrogate its decisions. When a high-value transfer or Razorpay payment is flagged or declined, the operator must be able to answer:
1. **WHAT happened?** (Identity, amount, channel, timestamp, and source provenance)
2. **WHY was it flagged?** (Risk score, risk tier, primary certified reason code, supporting codes, plain-English narrative)
3. **WHICH MODEL evaluated it?** (Model name, version, architecture type, SHA-256 artifact hash)
4. **WHICH POLICY was applied?** (Policy version, operating threshold $\theta^* = 0.990$, intermediate threshold $\theta_{\text{med}} = 0.900$, action)
5. **WHAT decision was made?** (`DECLINED`, `REVIEW_REQUIRED`, `CHALLENGED`, `APPROVED`)
6. **WHAT evidence was available at decision time?** (Observed point-in-time features, state velocities, cold-start flags)
7. **WAS the event anomalous?** (Heuristic and statistical anomaly signals: 100% balance drain, $>90\%$ liquidity drain, mule velocity)
8. **CAN I trace the decision?** (Audit event ID, evaluation ID, chained SHA-256 block hash, PII masking)
9. **WHAT SHOULD A HUMAN INVESTIGATOR DO NEXT?** (Deterministic, reason-code-guided review procedures without automated underwriting)

**Key Finding**:
The system already possesses rich underlying decision primitives (`ExplanationResolver`, `AuditEvent`, `AuditLogger`, `ReasonCodeCard`, `CausalEvidenceGrid`, `EngineTelemetry`, `InspectorPage.tsx`). However, these components are currently fragmented:
- `InspectorPage.tsx` depends on an ephemeral in-memory state passed via React props from `StreamPage.tsx`. Refreshing or deep-linking results in an empty screen (`No Transaction Selected`).
- There is no persistent backend endpoint to query an investigation dossier by ID (`GET /v1/investigations/{id}`).
- There is no unified **Investigation Queue** listing flagged events across live evaluations, Razorpay Test Mode webhooks, and benchmark demo fixtures.
- There is no deterministic **Human Investigator Guidance** mapping certified reason codes to structured operational next-steps.

---

## 2. Existing Investigation-Related Capabilities Found

```
==================================================================================================
EXISTING COMPONENT               CAPABILITY & DATA PROVIDED
==================================================================================================
1. ExplanationResolver           Produces deterministic ReasonDetails:
   (src/engine/explanation_      • 8 certified Reason Codes (RC_EXACT_BALANCE_DRAIN, RC_SEVERE_LIQUIDITY_DRAIN,
    resolver.py)                   RC_DEST_MULE_VELOCITY, RC_NEW_ACCOUNT_LARGE_OUTFLOW, RC_HIGH_RISK_CHANNEL_COMBO,
                                   RC_SENDER_AMOUNT_DEVIATION, RC_FALLBACK_EVALUATION_ACTIVE, RC_BENIGN_BASELINE)
                                 • Dynamic parametric English narratives (<1.0ms generation)
                                 • Point-in-time causal evidence dictionary (liquidation_pct, mule counters, etc.)

2. AuditLogger & AuditEvent      Stores up to 10,000 immutable decision blocks:
   (src/engine/audit_logger.py)  • event_id (aud_uuid), event_timestamp_utc, transaction_id, merchant_id
                                 • lineage (engine_version, model_version, model_type, model_hash, policy_version, threshold)
                                 • runtime_telemetry (latencies, fallback_mode_active)
                                 • input_snapshot_masked (PII-masked sender/recipient, old balances, amount, channel)
                                 • causal_features_extracted (15 or 36 feature values)
                                 • evaluation_result (raw_score, band, decision, action, primary_code, all_codes)
                                 • integrity_hash (chained SHA-256 block hash)

3. RazorpayWebhookAdapter        Stores up to 100 recent payment events:
   (src/engine/integrations/     • payment_id (pay_...), event_type, amount_inr, method, masked contact/vpa
    razorpay_adapter.py)         • evaluation_status (INSUFFICIENT_FEATURES vs EVALUATED_ENRICHED_TEST_MODE)
                                 • readiness_reason, missing_features, audit_id, chained event hash

4. Demo Fixtures (DEMO-01..09)   9 master competition scenarios covering the entire operational matrix:
   (frontend/src/api/client.ts)  • Benign consumer, severe liquidity drain, critical balance drain, cold-start,
                                   state outage fallback, tamper defense, explanation inspection, audit ledger, cost trade-off.

5. Existing UI Components        • RiskScoreGauge.tsx (Numeric dial with θ_med and θ* markers)
   (frontend/src/components/)    • ReasonCodeCard.tsx (Primary code pill, factor tags, plain-English summary)
                                 • CausalEvidenceGrid.tsx (Point-in-time feature matrix)
                                 • EngineTelemetry.tsx (Latency breakdown, model type, threshold applied)
                                 • DataSourceBadge.tsx (Visual tags distinguishing data provenance)
                                 • DecisionBadge.tsx (High-contrast action pills)
==================================================================================================
```

---

## 3. Missing Capabilities (Gaps to be Addressed in P1.2)

1. **Backend Investigation Service & API Endpoints**:
   - Currently, there is NO `GET /v1/investigations` to list investigable risk events.
   - Currently, there is NO `GET /v1/investigations/{id}` to fetch a complete, self-contained investigation dossier.
   - Operators cannot bookmark, link, or reload an investigation.
2. **Unified Investigation Queue**:
   - Need a consolidated queue combining:
     - Audit Ledger events (live evaluations)
     - Razorpay Test Mode webhook events
     - Standard Demo Fixtures (ensuring the workspace is fully functional and evaluatable on startup even before transactions are pushed).
3. **Deterministic Human Investigator Guidance**:
   - Need an explicit, deterministic mapping from certified Reason Codes to actionable, defense-only SOP (Standard Operating Procedure) steps for human risk officers.
4. **Deep Traceability UI**:
   - `InspectorPage.tsx` currently only shows the score and evidence cards; it does not show the cryptographic audit hash, block lineage, Razorpay provenance, or recommended investigation protocol.

---

## 4. Frozen Production Files Confirmed Protected

The following 9 core components remain strictly **100% FROZEN and UNTOUCHED**:

```
======================================================================================================================
FROZEN COMPONENT                 EXPECTED SHA-256 HASH                             RECONNAISSANCE STATUS
======================================================================================================================
model_b_stateful_hgb.joblib      5ea5926344e12215fe6e9fe91b593a99feb581747c...     VERIFIED (100% Byte-for-Byte Match)
model_a_causal_hgb.joblib        ea356eb3bd713de47c1cdc34389db461a02c95e8c...     VERIFIED (100% Byte-for-Byte Match)
policy_engine.py                 b61ab343af0e5aa84726db1d96700b89b8e22b88a...     VERIFIED (100% Byte-for-Byte Match)
decision_engine.py               1b5f1615f90548fa5eba94231e207d43d3e0bf7a6...     VERIFIED (100% Byte-for-Byte Match)
feature_pipeline.py              41b315ed0eaff96321d7dfabab72f5fdd1a254a39...     VERIFIED (100% Byte-for-Byte Match)
model_manager.py                 e2400085415e93554e480d8ff4f78fe22852c007f...     VERIFIED (100% Byte-for-Byte Match)
schemas.py                       de16b6bba9d2b235611adf52272ff033cb40eafff...     VERIFIED (100% Byte-for-Byte Match)
audit_logger.py                  044951b6a014a07cd48179cd9d5388373ddd2b4e0...     VERIFIED (100% Byte-for-Byte Match)
state_store.py                   f7f6615a0277bb11631fe4dbc0be5ddde26a1c288...     VERIFIED (100% Byte-for-Byte Match)
======================================================================================================================
```
- Production operating thresholds remain strictly frozen at $\theta^* = 0.990$ and $\theta_{\text{med}} = 0.900$.
- No model retraining, threshold tuning, or policy modification will occur.

---

## 5. Proposed File-by-File Modification Plan

```
==================================================================================================
FILE PATH                                        ACTION        RESPONSIBILITY & SAFETY
==================================================================================================
src/engine/investigations/investigation_service.py [NEW]       Read-only aggregation service that pulls from
                                                               audit_logger, webhook_adapter, and demo presets;
                                                               attaches deterministic SOP guidance; assembles dossiers.

tests/test_investigation_workspace.py            [NEW]         Comprehensive unit & contract tests for queue
                                                               listing, detail retrieval, 404 handling, and SOP mappings.

src/engine/api.py                                [MODIFY]      Mount read-only endpoints:
                                                               • GET /v1/investigations
                                                               • GET /v1/investigations/{id}

frontend/src/types/engine.ts                     [MODIFY]      Add TypeScript interfaces:
                                                               InvestigationSummary, InvestigationDetail, InvestigationGuidance.

frontend/src/api/client.ts                       [MODIFY]      Add fetcher methods:
                                                               getInvestigations(), getInvestigationDetail(id).

frontend/src/pages/InspectorPage.tsx             [MODIFY]      Transform InspectorPage into the complete
                                                               Investigation Workspace with queue + detail view,
                                                               audit ledger cross-link, and SOP guidance cards.

frontend/src/components/Navbar.tsx               [MODIFY]      Add "Investigation Workspace" navigation item.
==================================================================================================
```

---

## 6. Proposed API Contract

### Endpoint 1: `GET /v1/investigations?limit=50&band=HIGH_RISK`
- **Query Parameters**:
  - `limit`: int (default: 50, max: 100)
  - `band`: Optional[str] (`HIGH_RISK`, `MEDIUM_RISK`, `LOW_RISK`)
  - `provenance`: Optional[str] (`LIVE_EVALUATION`, `RAZORPAY_TEST_MODE`, `DEMO_FIXTURE`)
- **Response Format**:
  ```json
  [
    {
      "investigation_id": "inv_demo_03",
      "event_ref": "demo-03",
      "timestamp_iso": "2026-09-02T06:50:00Z",
      "source_provenance": "DEMO_FIXTURE",
      "transaction_type": "TRANSFER",
      "amount": 284100.50,
      "sender_masked": "C_VI***_03",
      "dest_masked": "C_MU***_03",
      "risk_score": 0.9984,
      "risk_band": "HIGH_RISK",
      "decision": "DECLINED",
      "action": "DECLINE",
      "primary_reason_code": "RC_EXACT_BALANCE_DRAIN",
      "model_version": "model_b_stateful_hgb_v1.0.0",
      "has_audit_record": true
    }
  ]
  ```

### Endpoint 2: `GET /v1/investigations/{investigation_id}`
- **Path Parameter**: `investigation_id` (str)
- **Response Format**:
  ```json
  {
    "investigation_id": "inv_demo_03",
    "event_ref": "demo-03",
    "timestamp_iso": "2026-09-02T06:50:00Z",
    "source_provenance": "DEMO_FIXTURE",
    "what_happened": {
      "transaction_id": "demo-03",
      "step": 452,
      "channel": "TRANSFER",
      "amount": 284100.50,
      "sender_masked": "C_VI***_03",
      "sender_old_balance": 284100.50,
      "dest_masked": "C_MU***_03",
      "dest_old_balance": 0.00
    },
    "why_flagged": {
      "risk_score": 0.9984,
      "risk_band": "HIGH_RISK",
      "primary_reason_code": "RC_EXACT_BALANCE_DRAIN",
      "all_reason_codes": ["RC_EXACT_BALANCE_DRAIN", "RC_HIGH_RISK_CHANNEL_COMBO"],
      "narrative": "Transaction attempts exact 100% liquidation of available sender balance ($284,100.50) via high-risk TRANSFER channel."
    },
    "model_lineage": {
      "model_name": "model_b_stateful_hgb_v1.0.0",
      "model_type": "MODEL_B_STATEFUL_HGB",
      "model_sha256": "5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735",
      "fallback_triggered": false
    },
    "policy_lineage": {
      "policy_version": "v1.2.0-frozen",
      "operating_threshold": 0.990,
      "decision": "DECLINED",
      "action": "DECLINE"
    },
    "available_evidence": {
      "liquidation_pct": 100.0,
      "channel": "TRANSFER",
      "is_sender_cold_start": 0,
      "dest_unique_orig_cnt": 1,
      "execution_latency_ms": 1.45
    },
    "anomaly_indicators": [
      { "signal": "EXACT_BALANCE_LIQUIDATION", "severity": "CRITICAL", "description": "100.0% of sender funds drained in single transfer." },
      { "signal": "ZERO_BALANCE_DESTINATION", "severity": "HIGH", "description": "Beneficiary account had zero pre-existing balance." }
    ],
    "investigator_guidance": {
      "urgency": "IMMEDIATE_ACTION",
      "recommended_action": "BLOCK_AND_VERIFY",
      "protocol_steps": [
        "1. Confirm customer authorization via out-of-band communication (SMS/voice challenge).",
        "2. Place provisional freeze on beneficiary account destination.",
        "3. Cross-reference sender device fingerprint and IP geolocation delta."
      ]
    },
    "audit_trail": {
      "audit_event_id": "aud_01829374-1234-abcd",
      "chained_integrity_hash": "a8f92b7c4d...",
      "tamper_evident_status": "VERIFIED_VALID"
    }
  }
  ```

---

## 7. Proposed UI Structure

We propose restructuring `InspectorPage.tsx` into a 2-panel professional **Risk Operations Workspace**:

1. **Left Panel: Investigation Queue & Filters**:
   - Filter chips: `All Events`, `High Risk Declines`, `Manual Review Required`, `Razorpay Webhooks`.
   - Search bar: Find by transaction ID, payment ID, or account masked string.
   - Interactive list cards showing: Risk Score badge, Action pill, Transaction ID, Masked Account, and Primary Reason Code.
2. **Right Panel: Deep Investigation Dossier**:
   - **Header Banner**: Decision summary, Risk Band, Decoupled Action (`DECLINE`, `MANUAL_REVIEW`, `STEP_UP_CHALLENGE`, `APPROVE`), and Data Provenance badge (`LIVE ENGINE`, `RAZORPAY TEST MODE`, `DEMO FIXTURE`).
   - **Dossier Tabs / Sections**:
     1. **Overview & Narrative**: Visual radial gauge, primary reason narrative, model version pill, policy version pill.
     2. **Causal Evidence Matrix**: 6-cell point-in-time feature grid.
     3. **Deterministic Investigator Guidance**: Step-by-step Standard Operating Procedure (SOP) tailored directly to the primary reason code.
     4. **Cryptographic Audit Trail**: SHA-256 block hash, event ID, lineage breakdown, and latency telemetry.

---

## 8. Test Plan

We will create `tests/test_investigation_workspace.py` verifying:
1. `GET /v1/investigations` returns 200 and a structured list of candidates.
2. Filtering by `band=HIGH_RISK` and `provenance=DEMO_FIXTURE` works accurately.
3. `GET /v1/investigations/{id}` returns complete 9-pillar dossier for valid IDs.
4. Non-existent IDs return HTTP 404 with structured error envelope.
5. Deterministic SOP guidance is present and accurate for all 8 reason codes.
6. Zero mutation of production engine state: `engine.evaluate()` produces identical scores before and after investigation queries.
7. All 9 frozen SHA-256 hashes remain 100% byte-for-byte identical.
8. `npm run build` succeeds with zero TypeScript errors.

---

## 9. Architectural Risks & Safety Evaluation

```
==================================================================================================
RISK DESCRIPTION                                                  SEVERITY   MITIGATION STRATEGY
==================================================================================================
1. Accidental coupling of investigation guidance to engine logic  CRITICAL   Keep investigation service purely
                                                                             read-only and additive in src/engine/investigations/.
                                                                             Zero modifications to decision_engine.py.

2. Inventing ungrounded investigation evidence                    HIGH       Only render features that exist in the
                                                                             AuditEvent, EvaluateResponse, or DemoFixture.

3. Fabricating Razorpay events                                    HIGH       Explicitly label local test webhooks as
                                                                             "Razorpay Test Mode" with zero live claims.

4. Client-side state loss on refresh                              MEDIUM     Store and query investigations via
                                                                             backend API (/v1/investigations/{id}).

5. Regressing frozen hashes                                       CRITICAL   Run automated hash checks before/after.
==================================================================================================
```

---

## 10. Final Recommendation: **SAFE TO PROCEED (GO)**

- **Safety**: Fully safe to implement. P1.2 requires **ZERO changes to the frozen decision engine, policy thresholds, ML artifacts, or schemas**.
- **User Experience**: Elevated to an enterprise-grade investigation console perfectly suited for viva defense and judge walkthroughs.

---

### STOP CONDITION SATISFIED
Reconnaissance complete. Implementation has NOT been started. Awaiting your approval to proceed!
