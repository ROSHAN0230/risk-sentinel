"""
Risk Sentinel — FastAPI Production Service
Exposes /v1/risk/evaluate, /v1/health, /v1/audit/events, and /v1/model/info.
"""

import sys
try:
    from sklearn._loss import _loss
    sys.modules['_loss'] = _loss
except Exception:
    pass

from fastapi import FastAPI, HTTPException, Request, status, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any, List, Optional

from src.engine.schemas import EvaluateRequest, EvaluateResponse
from src.engine.decision_engine import RiskDecisionEngine
from src.engine.infrastructure.redis_provider import create_configured_state_store
from src.engine.infrastructure.security import (
    SecurityHeadersMiddleware,
    verify_api_key,
    default_rate_limiter
)

app = FastAPI(
    title="Risk Sentinel — AI Risk Decision Engine",
    version="2.9.0",
    description="Defensive payment fraud detection and real-time causal risk management API."
)

# Enable CORS for external dashboard or cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# In-Memory Rate Limiting Middleware for API endpoints
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/v1/"):
        client_ip = request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "127.0.0.1")
        client_key = client_ip.split(",")[0].strip()
        default_rate_limiter.check_rate_limit(client_key)
    return await call_next(request)

# Initialize single global engine instance with configured state backend
engine = RiskDecisionEngine(state_store=create_configured_state_store())

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "INVALID_SCHEMA",
            "message": "Transaction payload failed schema validation.",
            "details": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ENGINE_ERROR",
            "message": str(exc)
        }
    )

@app.post(
    "/v1/risk/evaluate",
    response_model=EvaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate transaction risk in real time",
    dependencies=[Depends(verify_api_key)]
)
async def evaluate_transaction(request: EvaluateRequest):
    """
    Synchronously scores incoming transaction, extracts causal features,
    applies operating policy, generates explanations, and returns structured decision.
    """
    try:
        response = engine.evaluate(request)
        
        # Record into Persistent TransactionStore
        try:
            from src.engine.transaction_store import default_transaction_store, TransactionRecord, mask_account_id
            
            is_demo = "demo" in request.transaction_id.lower() or request.transaction_id.startswith("DEMO-") or request.transaction_id.startswith("tx_demo")
            prov = "DEMO_FIXTURE" if is_demo else "API_DIRECT"
            auto_resp = "CAPTURE_PERMITTED" if response.decision.value == "APPROVED" else "CAPTURE_SUPPRESSED"
            
            tx_rec = TransactionRecord(
                transaction_id=request.transaction_id,
                timestamp_iso=response.timestamp_iso,
                provenance=prov,
                amount_inr=request.amount,
                currency="INR",
                channel_type=request.type.value if hasattr(request.type, 'value') else str(request.type),
                sender_masked=mask_account_id(request.nameOrig),
                dest_masked=mask_account_id(request.nameDest),
                merchant_id=request.merchant_id or "default_merchant",
                risk_score=response.risk_score,
                risk_band=response.risk_band.value if hasattr(response.risk_band, 'value') else str(response.risk_band),
                decision=response.decision.value if hasattr(response.decision, 'value') else str(response.decision),
                policy_action=response.action.value if hasattr(response.action, 'value') else str(response.action),
                primary_reason_code=response.reasons.primary_code,
                reasons_narrative=response.reasons.narrative,
                auto_response_action=auto_resp,
                auto_response_status="DIRECT_EVALUATION",
                model_version=response.engine_metadata.model_version,
                policy_version=response.engine_metadata.policy_version,
                audit_event_id=response.evaluation_id,
                integrity_hash=response.evaluation_id
            )
            default_transaction_store.record(tx_rec)
        except Exception:
            pass

        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/v1/health", summary="Service health check")
async def health_check():
    state_ok = engine.state_store.health_check()
    return {
        "status": "HEALTHY" if state_ok else "DEGRADED",
        "engine_version": engine.engine_version,
        "state_store_responsive": state_ok,
        "champion_model_sha256": engine.model_manager.model_b_sha256
    }

@app.get("/v1/model/info", summary="Model lineage and frozen metadata")
async def get_model_info():
    return engine.model_manager.manifest

@app.get(
    "/v1/audit/events",
    summary="Query recent immutable audit events",
    dependencies=[Depends(verify_api_key)]
)
async def get_audit_events(limit: int = 50):
    return engine.audit_logger.get_events(limit=limit)

from src.engine.integrations.razorpay_adapter import (
    RazorpayWebhookAdapter,
    WebhookConfigureRequest,
    RazorpayWebhookStatus,
    WebhookContractTestRequest,
    WebhookContractTestResponse,
    NormalizedWebhookEvent
)

webhook_adapter = RazorpayWebhookAdapter(engine=engine)

@app.post(
    "/v1/webhooks/razorpay",
    summary="Receive and process Razorpay Test Mode webhooks",
    status_code=status.HTTP_200_OK
)
async def handle_razorpay_webhook(request: Request):
    """
    Ingests raw Razorpay Test Mode payment events, verifies HMAC-SHA256 signature,
    enforces idempotency, applies model-readiness evaluation, and audits the event.
    """
    raw_body = await request.body()
    sig_header = request.headers.get("X-Razorpay-Signature")
    normalized_event, status_code = webhook_adapter.process_webhook(
        raw_body=raw_body,
        signature_header=sig_header
    )
    if status_code != 200:
        return JSONResponse(status_code=status_code, content=normalized_event.model_dump())
    return normalized_event.model_dump()

@app.get(
    "/v1/webhooks/events",
    summary="Query recent normalized Razorpay Test Mode webhook events"
)
async def get_webhook_events(limit: int = 50):
    """Returns recent normalized Razorpay Test Mode webhook events."""
    return [ev.model_dump() for ev in webhook_adapter.get_recent_events(limit=limit)]

@app.post(
    "/v1/integrations/razorpay/webhook/configure",
    summary="Configure Razorpay Webhook Secret for HMAC verification",
    response_model=RazorpayWebhookStatus
)
async def configure_razorpay_webhook(request: WebhookConfigureRequest):
    """
    Configures the Razorpay Webhook secret in server memory for HMAC-SHA256 signature verification.
    The secret is never stored in persistent browser storage or returned in unmasked format.
    """
    razorpay_live_service._webhook_secret = request.webhook_secret.strip()
    return webhook_adapter.configure_secret(request.webhook_secret)

@app.get(
    "/v1/integrations/razorpay/webhook/status",
    summary="Get Razorpay Webhook configuration and delivery status",
    response_model=RazorpayWebhookStatus
)
async def get_razorpay_webhook_status():
    """Returns the current webhook secret status, masked token, endpoint URL, and delivery counters."""
    return webhook_adapter.get_status()

@app.post(
    "/v1/integrations/razorpay/webhook/clear",
    summary="Clear active Webhook Secret",
    response_model=RazorpayWebhookStatus
)
async def clear_razorpay_webhook():
    """Clears the active webhook secret from server memory."""
    razorpay_live_service._webhook_secret = None
    return webhook_adapter.clear_secret()

@app.post(
    "/v1/integrations/razorpay/webhook/test-contract",
    summary="Execute signed Razorpay-compatible Webhook Contract Test",
    response_model=WebhookContractTestResponse
)
async def test_razorpay_webhook_contract(request: WebhookContractTestRequest):
    """
    Generates a cryptographically signed Razorpay-compatible test event,
    submits it to the webhook processing pipeline, evaluates risk, and audits the result.
    Tagged explicitly with provenance: SIMULATED_CONTRACT_TEST.
    """
    return webhook_adapter.generate_and_process_contract_test(request)

from src.engine.integrations.razorpay_capture_gate import RazorpayCaptureGate, RazorpayCaptureRequest
from src.engine.integrations.razorpay_live_service import (
    RazorpayLiveService,
    RazorpayConnectRequest,
    RazorpayConnectionStatus,
    CreateOrderRequest,
    CreateOrderResponse,
    ProcessCheckoutRequest,
    LiveVerificationResult,
    SelfTestResponse
)

capture_gate = RazorpayCaptureGate(engine=engine)
razorpay_live_service = RazorpayLiveService(engine=engine)

@app.post(
    "/v1/gate/evaluate-and-capture",
    summary="Merchant-Controlled Razorpay Test Mode Capture Gate",
    description="Evaluates payments in 'authorized' state against the frozen engine and executes capture if approved.",
    dependencies=[Depends(verify_api_key)]
)
async def evaluate_and_capture_gate(request: RazorpayCaptureRequest):
    """
    Evaluates an authorized payment through the frozen Risk Sentinel engine.
    If approved, dispatches the capture action. If held or declined, suppresses capture.
    """
    result = capture_gate.evaluate_and_capture(request)
    return result.model_dump()

@app.get(
    "/v1/gate/events",
    summary="Fetch Recent Razorpay Capture Gate Events"
)
async def get_gate_events(limit: int = Query(50, ge=1, le=100)):
    """Returns recent capture gate evaluations and actions."""
    events = capture_gate.get_recent_gate_events(limit=limit)
    return [e.model_dump() for e in events]

# --- Live Razorpay Test Mode Gateway Endpoints ---

@app.post(
    "/v1/integrations/razorpay/connect",
    summary="Connect and validate Razorpay Test Mode credentials",
    response_model=RazorpayConnectionStatus
)
async def connect_razorpay(request: RazorpayConnectRequest):
    """
    Connects Razorpay Test credentials (rzp_test_...).
    Strictly validates format and performs read-only self check against Razorpay API.
    Rejects rzp_live_ keys immediately.
    """
    try:
        status = razorpay_live_service.connect(
            key_id=request.key_id,
            key_secret=request.key_secret,
            webhook_secret=request.webhook_secret
        )
        # Also sync key to capture gate and webhook adapter
        capture_gate.key_id = razorpay_live_service.key_id
        capture_gate.key_secret = razorpay_live_service.key_secret
        capture_gate.has_live_credentials = razorpay_live_service.has_live_credentials
        if request.webhook_secret:
            webhook_adapter.webhook_secret = request.webhook_secret
        return status
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error connecting to Razorpay: {str(e)}")

@app.get(
    "/v1/integrations/razorpay/status",
    summary="Get current Razorpay Test Mode connection status",
    response_model=RazorpayConnectionStatus
)
async def get_razorpay_status():
    """Returns current Razorpay Test Mode connectivity and masked key information."""
    return razorpay_live_service.get_status()

@app.post(
    "/v1/integrations/razorpay/disconnect",
    summary="Disconnect Razorpay credentials",
    response_model=RazorpayConnectionStatus
)
async def disconnect_razorpay():
    """Clears currently active Razorpay Test credentials."""
    status = razorpay_live_service.disconnect()
    capture_gate.key_id = None
    capture_gate.key_secret = None
    capture_gate.has_live_credentials = False
    return status

@app.post(
    "/v1/integrations/razorpay/orders",
    summary="Create a Razorpay Test Mode Order with manual capture",
    response_model=CreateOrderResponse
)
async def create_razorpay_order(request: CreateOrderRequest):
    """
    Creates a real Razorpay Order with payment_capture: 0 (manual capture mode)
    enabling Risk Sentinel's pre-capture merchant risk gate.
    """
    try:
        return razorpay_live_service.create_order(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay Order: {str(e)}")

@app.post(
    "/v1/integrations/razorpay/checkout/process",
    summary="Process Razorpay Standard Checkout payment and execute risk gate"
)
async def process_checkout_payment(request: ProcessCheckoutRequest):
    """
    End-to-end checkout handler:
    1. Verifies checkout signature (HMAC-SHA256).
    2. Fetches payment from Razorpay API.
    3. Evaluates transaction through frozen Risk Sentinel engine.
    4. Permitting capture only on APPROVE; strictly suppressing capture on REVIEW/DECLINE.
    5. Records into TransactionStore and updates audit ledger.
    """
    try:
        return razorpay_live_service.process_checkout_payment(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout processing error: {str(e)}")

@app.get(
    "/v1/integrations/razorpay/verify/{payment_id}",
    summary="Cross-verify Risk Sentinel decision vs live Razorpay state",
    response_model=LiveVerificationResult
)
async def verify_razorpay_payment(payment_id: str):
    """
    Fetches live payment status directly from Razorpay API (GET /v1/payments/{payment_id})
    and compares it against local TransactionStore decision for discrepancy detection.
    """
    return razorpay_live_service.verify_live_payment_crosscheck(payment_id)

@app.get(
    "/v1/integrations/razorpay/self-test",
    summary="Run 9-point Razorpay Test Mode integration self-test",
    response_model=SelfTestResponse
)
async def run_razorpay_self_test():
    """
    Executes an automated 9-point self-test suite testing credentials,
    API connectivity, order creation, HMAC signature verification,
    pre-capture risk evaluation, and capture suppression safety invariants.
    """
    return razorpay_live_service.run_self_test()


from src.engine.transaction_store import default_transaction_store, TransactionRecord

@app.get(
    "/v1/transactions",
    summary="Query real-time persisted transaction stream & auto-response records",
    response_model=List[TransactionRecord]
)
async def get_transactions_endpoint(
    limit: int = Query(50, ge=1, le=200),
    provenance: Optional[str] = Query(None, description="Filter by provenance (GENUINE_RAZORPAY_TEST_MODE, SIMULATED_CONTRACT_TEST, DEMO_FIXTURE, API_DIRECT)"),
    decision: Optional[str] = Query(None, description="Filter by decision (APPROVED, REVIEW_REQUIRED, DECLINED)")
):
    """Returns recent persisted transaction monitoring records with provenance and auto-response actions."""
    return default_transaction_store.get_transactions(limit=limit, provenance=provenance, decision=decision)

@app.get(
    "/v1/transactions/summary",
    summary="Query summary statistics across all monitored transactions"
)
async def get_transactions_summary_endpoint():
    """Returns aggregated transaction metrics by provenance, decision, and auto-response action."""
    return default_transaction_store.get_summary()

@app.get(
    "/v1/transactions/{transaction_id}",
    summary="Fetch single monitored transaction details"
)
async def get_transaction_by_id_endpoint(transaction_id: str):
    """Retrieves single transaction record by ID."""
    record = default_transaction_store.get_by_id(transaction_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")
    return record.model_dump()

from src.engine.analytics.economics_service import EconomicsService

economics_service = EconomicsService()

@app.get(
    "/v1/analytics/threshold-sensitivity",
    summary="Query empirical 15-point validation threshold sensitivity ladder"
)
async def get_threshold_sensitivity():
    """Returns the measured 15-point validation threshold sensitivity records."""
    return economics_service.get_threshold_sensitivity()

@app.get(
    "/v1/analytics/cost-simulation",
    summary="Simulate decision economics and friction cost across validation thresholds"
)
async def get_cost_simulation(alpha: float = Query(0.01, description="Intervention friction multiplier (0.001 to 0.05)")):
    """
    Computes economic loss (Missed Fraud Dollars + alpha * Flagged Legitimate Volume)
    across the validation threshold ladder for a given friction parameter alpha.
    """
    try:
        return economics_service.simulate_cost(alpha=alpha)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get(
    "/v1/analytics/benchmark-summary",
    summary="Fetch Canonical Held-Out Future Test Benchmark Summary",
    description="Returns the authoritative PaySim future held-out test evaluation metrics, confusion matrix, and financial outcomes."
)
async def get_benchmark_summary_endpoint():
    """
    Returns canonical held-out evaluation metrics from the authoritative serialized artifacts.
    Read-only: zero production state mutation, zero threshold change.
    """
    try:
        return economics_service.get_benchmark_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/v1/analytics/model-drift",
    summary="Fetch Model Distribution Drift & PSI Report",
    description="Returns the measured Population Stability Index (PSI) and monitoring band comparing reference validation vs future test slices."
)
async def get_model_drift_endpoint():
    """
    Returns the empirical Population Stability Index (PSI) report.
    Provenance: OFFLINE_SIMULATED_BENCHMARK_SLICES.
    """
    import os
    import json
    report_path = os.path.join("research", "phase4", "artifacts", "model_drift_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Model drift report not found.")

from src.engine.analytics.replay_service import ReplayService, ReplayRequest

replay_service = ReplayService(prod_engine=engine)

@app.post(
    "/v1/replay/evaluate",
    summary="Judge-Facing Fraud Decision Replay",
    description="Evaluates hypothetical or modified transaction context within an isolated sandbox without mutating production state or audit ledgers.",
    dependencies=[Depends(verify_api_key)]
)
async def evaluate_replay_endpoint(request: ReplayRequest):
    """
    Executes an isolated decision replay. Recomputes features, score, reasons, policy,
    and economic impact with zero production side effects.
    """
    try:
        result = replay_service.evaluate_replay(request)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from src.engine.investigations.investigation_service import InvestigationService

investigation_service = InvestigationService(engine=engine, webhook_adapter=webhook_adapter)

@app.get(
    "/v1/investigations",
    summary="List recent investigable risk events across audit ledger, webhooks, and demo fixtures"
)
async def list_investigations(
    limit: int = Query(50, ge=1, le=100),
    band: Optional[str] = Query(None, description="Filter by risk band (e.g. HIGH_RISK, MEDIUM_RISK)"),
    provenance: Optional[str] = Query(None, description="Filter by provenance (AUDIT_LEDGER, RAZORPAY_TEST_MODE, DEMO_FIXTURE)")
):
    """Returns deduplicated investigation summaries with explicit source provenance."""
    summaries = investigation_service.list_investigations(limit=limit, band=band, provenance=provenance)
    return [s.model_dump() for s in summaries]

@app.get(
    "/v1/investigations/{investigation_id}",
    summary="Fetch comprehensive 9-pillar investigation dossier for a specific risk event"
)
async def get_investigation_detail(investigation_id: str):
    """Returns the complete 9-pillar investigation dossier including deterministic SOP guidance."""
    detail = investigation_service.get_investigation_detail(investigation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Investigation record '{investigation_id}' not found.")
    return detail.model_dump()

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve Frontend static assets if built
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("v1/"):
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = os.path.join(frontend_dist, full_path)
        if os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

