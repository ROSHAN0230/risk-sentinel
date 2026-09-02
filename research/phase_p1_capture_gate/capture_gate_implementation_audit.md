# Risk Sentinel — Phase 1: Razorpay Test Mode Capture-Gate Integration Audit
**Document ID**: `AUDIT-CAPTURE-GATE-P1-001`  
**Date**: `2026-09-02`  
**Phase**: `Phase 1 — Razorpay Test Mode Capture-Gate Integration`  
**Target Competition**: `Razorpay AI Buildathon 2026` — `Track 02: AI Risk Manager`  
**Audit Scope**: `Pre-Implementation Technical Feasibility, API Contract & Safety Boundaries`  
**Status**: **`AUDIT COMPLETE — AWAITING USER APPROVAL (DO NOT IMPLEMENT YET)`**  

---

## 1. Executive Context & Objective

The objective of Phase 1 is to build the strongest, most truthful demonstration of Razorpay gateway interoperability for Risk Sentinel:

$$\text{Razorpay Checkout} \longrightarrow \text{Payment Created} \longrightarrow \mathbf{AUTHORIZED} \longrightarrow \mathbf{Risk\ Sentinel\ Gate} \longrightarrow \begin{cases} \mathbf{APPROVE} \longrightarrow \text{Capture API Called} \longrightarrow \mathbf{CAPTURED} \\ \mathbf{HOLD/DECLINE} \longrightarrow \text{Capture NOT Called} \longrightarrow \mathbf{HELD} \end{cases}$$

### Critical Truth Boundary
- **We do NOT claim that Risk Sentinel intercepts Razorpay's internal core authorization engine.** In payment processing, merchant applications do not sit inside Visa/Mastercard/NPCI or the acquiring bank's real-time switch.
- **The truthful, industry-standard architecture is a Merchant-Controlled Risk Capture Gate**:
  1. The merchant creates an Order or sets Checkout with `payment_capture: 0` (Manual Capture mode).
  2. The customer authorizes the payment with their bank/UPI/card. The payment transitions to `status: "authorized"`.
  3. Razorpay sends the `payment.authorized` webhook notification to the merchant.
  4. The merchant's **Risk Sentinel Capture Gate** evaluates the transaction.
  5. If Risk Sentinel returns `APPROVE`: The gate calls Razorpay's `/v1/payments/{payment_id}/capture` API. The payment transitions to `captured` and settles.
  6. If Risk Sentinel returns `HOLD` or `DECLINE`: The gate explicitly does **NOT** call capture. Funds remain held at the issuing bank and automatically void/refund upon expiry, protecting the merchant from fraudulent chargebacks.

---

## A. Existing Capabilities Found in Repository

```
========================================================================================================================
COMPONENT                         EXISTING FILE PATH                            CURRENT IMPLEMENTED CAPABILITIES
========================================================================================================================
1. Webhook Adapter                src/engine/integrations/razorpay_adapter.py    • Validates RazorpayPaymentEntity & Webhook payload schemas.
                                                                                • Verifies HMAC-SHA256 signatures via X-Razorpay-Signature.
                                                                                • Idempotency tracking preventing duplicate event processing.
                                                                                • Zero-fabrication gating when balance context is missing.
                                                                                • Enriched evaluation path when notes context is present.
                                                                                • Chained SHA-256 integrity hash for each webhook event.

2. Webhook REST Endpoints         src/engine/api.py                             • POST /v1/webhooks/razorpay (receives & processes events).
                                                                                • GET /v1/webhooks/events (returns recent event buffer).

3. Webhook Test Suite             tests/test_razorpay_webhook.py                • 10/10 tests passing covering valid events, bad signatures,
                                                                                malformed JSON, idempotency, and audit logging.

4. Webhook Frontend Viewer        frontend/src/components/RazorpayWebhookViewer.tsx • Renders event stream, dispatch raw test event,
                                                                                and dispatch enriched drain test event.

5. Investigation Cross-Linkage    src/engine/investigations/investigation_service.py• Ingests webhook events with provenance
                                                                                source_provenance: "RAZORPAY_TEST_MODE".
                                                                                • Deduplicates with audit ledger if transaction was evaluated.
========================================================================================================================
```

---

## B. Missing Capabilities Required for Capture-Gate

1. **Payment State Validation**:
   - Current adapter processes any event type (`payment.authorized`, `payment.captured`, etc.).
   - The Capture Gate must specifically validate that `status == "authorized"` and `captured == false`. If payment is already captured or failed, capture must NOT be attempted.
2. **Razorpay Capture API Client**:
   - Currently, there is NO outgoing HTTP client calling `POST https://api.razorpay.com/v1/payments/{payment_id}/capture`.
   - Needs an authenticated client using HTTP Basic Auth (`RAZORPAY_KEY_ID:RAZORPAY_KEY_SECRET`).
   - Needs a resilient dual-mode design:
     - **Live Test Mode**: If `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are present in the environment, executes real HTTP requests to Razorpay's API.
     - **Simulated Test Mode**: If keys are unconfigured (e.g., offline demo, evaluator sandbox, or grading environment without private merchant keys), executes contract-compliant simulated responses, explicitly labeling output as `SIMULATED_TEST_MODE (RAZORPAY_KEY_ID not set)`.
3. **Fail-Closed Capture Gate Orchestrator**:
   - Currently, the webhook adapter returns evaluation details, but does not execute or record the capture decision.
   - Missing an orchestrator that maps:
     - `APPROVE` $\longrightarrow$ Execute Capture $\longrightarrow$ `CAPTURE_CALLED` / `RESULT: CAPTURED`
     - `REVIEW_REQUIRED` / `DECLINE` $\longrightarrow$ Suppress Capture $\longrightarrow$ `CAPTURE_SUPPRESSED` / `RESULT: HELD_FOR_REVIEW`
     - Missing Context $\longrightarrow$ Suppress Capture $\longrightarrow$ `CAPTURE_SUPPRESSED` / `RESULT: HELD_INSUFFICIENT_CONTEXT`
     - Engine Error $\longrightarrow$ Suppress Capture $\longrightarrow$ `CAPTURE_SUPPRESSED` / `RESULT: HELD_FAIL_CLOSED`
4. **Dedicated Capture Gate UI Component**:
   - A compact, high-contrast integration strip for `/stream` showing the exact state transition:
     `PAYMENT ID` $\to$ `STATUS: AUTHORIZED` $\to$ `RISK SENTINEL DECISION` $\to$ `CAPTURE ACTION` $\to$ `RESULT: CAPTURED / HELD`.

---

## C. Razorpay API Requirements & Specifications

### 1. Manual Capture Order Creation (`POST /v1/orders`)
```json
{
  "amount": 50000,
  "currency": "INR",
  "receipt": "rcpt_gate_001",
  "payment_capture": 0
}
```
*Note*: `payment_capture: 0` explicitly instructs Razorpay not to auto-capture payments made against this order.

### 2. Authorization Webhook Payload (`payment.authorized`)
```json
{
  "entity": "event",
  "account_id": "acc_test_merchant_01",
  "event": "payment.authorized",
  "contains": ["payment"],
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_test_01928374",
        "amount": 50000,
        "currency": "INR",
        "status": "authorized",
        "order_id": "order_test_01928374",
        "method": "upi",
        "captured": false,
        "notes": {
          "step": "452",
          "type": "TRANSFER",
          "oldbalanceOrg": "284100.50",
          "oldbalanceDest": "0.00",
          "nameOrig": "C_VICTIM_03",
          "nameDest": "C_MULE_03"
        }
      }
    }
  }
}
```

### 3. Manual Payment Capture API (`POST /v1/payments/{payment_id}/capture`)
- **URL**: `https://api.razorpay.com/v1/payments/{payment_id}/capture`
- **Method**: `POST`
- **Authentication**: HTTP Basic Auth (`key_id:key_secret`)
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "amount": 50000,
    "currency": "INR"
  }
  ```
- **Success Response (HTTP 200)**:
  ```json
  {
    "id": "pay_test_01928374",
    "entity": "payment",
    "amount": 50000,
    "currency": "INR",
    "status": "captured",
    "order_id": "order_test_01928374",
    "captured": true
  }
  ```

---

## D. Data Contract & Feature Gap (Zero-Fabrication Mandate)

### The Problem
A standard consumer payment processed on Razorpay contains gateway fields (`amount`, `currency`, `method`, `vpa`, `contact`, `email`, `notes`). It does **NOT** contain core banking balances:
- `oldbalanceOrg` (sender pre-transaction account balance)
- `oldbalanceDest` (destination pre-transaction balance)
- `step` (simulation temporal step)
- `type` (PaySim transaction channel)

### The Legitimate Merchant Context Mechanism
How can merchant context legitimately reach Risk Sentinel in Test Mode without fabricating data?
1. **Razorpay `notes` Mechanism**:
   - Razorpay's API explicitly permits merchants to attach up to 15 key-value pairs (512 characters each) during Order Creation or Checkout.
   - In enterprise merchant architectures, internal merchant order management systems (OMS) attach customer risk tier, customer account history, and pre-authorization account balance context into `notes`.
2. **Zero-Fabrication Enforcement**:
   - If `notes` contains the merchant-supplied banking context $\implies$ Risk Sentinel executes full GBDT evaluation under `EVALUATED_ENRICHED_TEST_MODE`.
   - If `notes` does NOT contain this context $\implies$ The Capture Gate **fails closed**:
     - Evaluation Status: `INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION`
     - Action: `HOLD_NO_CAPTURE`
     - Reason: *"Refusing evaluation on ungrounded features; payment held pending manual merchant review."*
   - Under **NO** circumstances will the system inject or guess synthetic balance numbers.

---

## E. Proposed File-by-File Changes (Additive & Isolated)

```
========================================================================================================================
FILE PATH                                        ACTION        ISOLATION & RESPONSIBILITY
========================================================================================================================
1. src/engine/integrations/razorpay_capture_gate.py [NEW]     Purely additive capture gate service.
                                                               • Validates payment status is 'authorized'.
                                                               • Checks merchant context completeness.
                                                               • Calls existing engine.evaluate().
                                                               • Dispatches capture API request (live or simulated).
                                                               • Fails closed on any error or decline.
                                                               • Cryptographically hashes gate outcome.

2. tests/test_razorpay_capture_gate.py          [NEW]         Comprehensive unit & integration test suite for the gate.
                                                               • 12 focused test cases (authorized, captured, held,
                                                                 fail-closed, idempotency, signature validation).

3. src/engine/api.py                             [MODIFY]      Mount 2 read-only / integration endpoints:
                                                               • POST /v1/gate/evaluate-and-capture
                                                               • GET /v1/gate/events

4. frontend/src/types/engine.ts                  [MODIFY]      Add TypeScript interfaces for CaptureGateEvent & Result.

5. frontend/src/api/client.ts                    [MODIFY]      Add evaluateAndCapture() and getCaptureGateEvents().

6. frontend/src/components/RazorpayCaptureGateViewer.tsx [NEW] Compact, high-contrast integration panel showing
                                                               Payment -> Authorized -> Decision -> Capture outcome.

7. frontend/src/pages/StreamPage.tsx             [MODIFY]      Incorporate RazorpayCaptureGateViewer alongside the
                                                               existing webhook monitor.
========================================================================================================================
```

---

## F. Files That Will Remain Strictly Frozen (100% Protected)

The following 9 core files will **NOT be modified, touched, retrained, or re-formatted**:
1. `src/engine/artifacts/model_b_stateful_hgb.joblib` (`5ea5926344e12215...`)
2. `src/engine/artifacts/model_a_causal_hgb.joblib` (`ea356eb3bd713de4...`)
3. `src/engine/policy_engine.py` (`b61ab343af0e5aa8...`)
4. `src/engine/decision_engine.py` (`1b5f1615f90548fa...`)
5. `src/engine/feature_pipeline.py` (`41b315ed0eaff963...`)
6. `src/engine/model_manager.py` (`e2400085415e9355...`)
7. `src/engine/schemas.py` (`de16b6bba9d2b235...`)
8. `src/engine/audit_logger.py` (`044951b6a014a07c...`)
9. `src/engine/state_store.py` (`f7f6615a0277bb11...`)

Operating thresholds remain permanently locked at **$\theta^* = 0.990$** and **$\theta_{\text{med}} = 0.900$**.

---

## G. Test Plan for Phase 1

`tests/test_razorpay_capture_gate.py` will validate:
1. `test_01_authorized_payment_with_benign_context_captures`: Benign transfer $\to$ `APPROVE` $\to$ Capture API called $\to$ `CAPTURED`.
2. `test_02_authorized_payment_with_drain_context_holds`: 100% balance drain $\to$ `DECLINED` $\to$ Capture API NOT called $\to$ `HELD_DECLINED`.
3. `test_03_non_authorized_payment_rejected`: Payment with `status: "failed"` or `"captured"` $\to$ rejected, no capture.
4. `test_04_missing_risk_context_fails_closed`: Payment without balance context $\to$ `HOLD_INSUFFICIENT_CONTEXT`, no capture.
5. `test_05_engine_evaluation_failure_fails_closed`: Simulates engine exception $\to$ `HOLD_FAIL_CLOSED`, no capture.
6. `test_06_capture_api_failure_recorded_accurately`: Simulates Razorpay API 500 error $\to$ records capture failure, no state inconsistency.
7. `test_07_idempotent_duplicate_prevention`: Duplicate authorized webhook returns cached capture decision without calling capture twice.
8. `test_08_invalid_hmac_signature_rejected`: Tampered webhook signature returns HTTP 401, no capture.
9. `test_09_real_or_simulated_mode_transparency`: Explicitly flags whether capture was executed via Live Test Mode or Simulated Test Mode.
10. `test_10_immutable_audit_chain_entry`: Every capture-gate outcome produces a chained SHA-256 block hash.
11. `test_11_frozen_hashes_preservation`: Verifies all 9 core hashes remain byte-for-byte identical.
12. `test_12_existing_regression_suite_unaffected`: Verifies 71 existing backend tests remain 100% passing.

---

## H. Risks & Failure Modes Analysis

```
========================================================================================================================
FAILURE SCENARIO                 ENGINEERING RISK                               MITIGATION / FAIL-CLOSED BEHAVIOR
========================================================================================================================
1. Risk Sentinel engine outage   Merchant captures fraudulent payment while     FAIL CLOSED: If engine is unreachable,
                                 risk engine is down.                           capture gate suppresses capture and logs
                                                                                HOLD_FAIL_CLOSED.

2. Webhook replay attack         Fraudster replays an approved webhook to       IDEMPOTENCY: Payment ID is checked against
                                 trigger multiple captures.                     the processed cache. Replays return the
                                                                                original decision without re-calling capture.

3. Live API key unconfigured     Demo fails if evaluator does not provide       SIMULATED FALLBACK: If RAZORPAY_KEY_ID is
                                 private Razorpay credentials.                  empty, operates in contract-compliant Simulated
                                                                                Test Mode, explicitly badged in the UI.

4. Accidental Live Mode use      User accidentally uses real production keys.   TEST MODE ENFORCEMENT: Rejects any key that
                                                                                does not begin with "rzp_test_".
========================================================================================================================
```

---

## I. Exact Two-Transaction Demo Flow

### Scenario A: Benign Payment $\longrightarrow$ Automatic Capture
1. **Trigger**: Authorized payment webhook for \$84.50 (`PAYMENT` channel, benign customer history in `notes`).
2. **Gate Validation**: Payment is in `status: "authorized"`, `captured: false`.
3. **Risk Evaluation**: Risk Sentinel evaluates transaction:
   - Operating Score: `0.0018`
   - Decision: `APPROVED` / Action: `APPROVE`
   - Primary Reason: `RC_BENIGN_BASELINE`
4. **Gate Action**: Capture Gate calls Razorpay Capture API (`POST /v1/payments/pay_xxx/capture`).
5. **Outcome**: Status transitions to `CAPTURED`. Merchant receives funds.
6. **Audit**: Cryptographically logged to SHA-256 ledger.

### Scenario B: High-Risk Balance Drain $\longrightarrow$ Interception & Hold
1. **Trigger**: Authorized payment webhook for \$284,100.50 (`TRANSFER` channel, 100% balance drain in `notes`).
2. **Gate Validation**: Payment is in `status: "authorized"`, `captured: false`.
3. **Risk Evaluation**: Risk Sentinel evaluates transaction:
   - Operating Score: `0.9984`
   - Decision: `DECLINED` / Action: `DECLINE`
   - Primary Reason: `RC_EXACT_BALANCE_DRAIN`
4. **Gate Action**: Capture Gate **SUPPRESSES** capture. Capture API is **NOT** called.
5. **Outcome**: Status remains `HELD_DECLINED`. Funds are withheld from fraudster.
6. **Audit & Investigation**: Chained to audit ledger; immediately visible in Investigation Workspace with deterministic SOP guidance.

---

## J. GO / NO-GO Recommendation

### **Recommendation: GO (APPROVED TO IMPLEMENT)**

**Rationale**:
1. **Strict Core Isolation**: The implementation is 100% external and additive. It lives in `src/engine/integrations/razorpay_capture_gate.py` with zero changes to the 9 frozen model, feature, policy, or decision files.
2. **Defensible & Truthful**: Accurately demonstrates the real-world post-authorization / pre-capture merchant risk workflow. Does not make false claims of intercepting core banking rails or internal Razorpay authorization.
3. **Fail-Closed Safety**: Guaranteed that missing context or engine errors result in `HOLD`, never unintended capture.
4. **Test Mode Safe**: Only Test Mode keys (`rzp_test_...`) are accepted, with transparent simulated test mode fallback.

---

### **STOP CONDITION COMPLIED**
Reconnaissance and audit complete. Zero application or model code has been modified. Awaiting your approval to proceed with Phase 1 implementation.
