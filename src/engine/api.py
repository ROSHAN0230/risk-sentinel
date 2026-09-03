"""
Risk Sentinel — FastAPI Production Service
Exposes /v1/risk/evaluate, /v1/health, /v1/audit/events, and /v1/model/info.
"""

from fastapi import FastAPI, HTTPException, Request, status, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any, List, Optional

from src.engine.schemas import EvaluateRequest, EvaluateResponse
from src.engine.decision_engine import RiskDecisionEngine
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

# Initialize single global engine instance
engine = RiskDecisionEngine()

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

from src.engine.integrations.razorpay_adapter import RazorpayWebhookAdapter

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

from src.engine.integrations.razorpay_capture_gate import RazorpayCaptureGate, RazorpayCaptureRequest

capture_gate = RazorpayCaptureGate(engine=engine)

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

