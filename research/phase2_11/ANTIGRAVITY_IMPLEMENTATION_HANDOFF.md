# Risk Sentinel — Frontend-to-Backend Integration Guide
**Document ID**: `INT-HND-2.11-001`  
**Status**: `FROZEN BACKEND INTEGRATION HANDOFF`  
**Backend Target**: `FastAPI Service (src/engine/api.py)`  

---

## 1. Direct API Integration Endpoints

```
[Google Stitch Frontend UI / React / Next.js / Vite]
                        │
                        ▼ (HTTP JSON REST)
┌────────────────────────────────────────────────────────┐
│ FastAPI Backend Server (http://localhost:8000)         │
├────────────────────────────────────────────────────────┤
│ 1. POST /v1/risk/evaluate   ──> Synchronous Evaluation │
│ 2. GET  /v1/health          ──> Engine Telemetry       │
│ 3. GET  /v1/model/info      ──> Model Lineage Manifest │
│ 4. GET  /v1/audit/events    ──> Immutable Audit Ledger │
└────────────────────────────────────────────────────────┘
```

---

## 2. Standard Client Invocation Examples

### TypeScript / Fetch Interface Example

```typescript
export interface EvaluateRequest {
  transaction_id: string;
  step: number;
  type: 'TRANSFER' | 'CASH_OUT' | 'PAYMENT' | 'CASH_IN' | 'DEBIT';
  amount: number;
  nameOrig: string;
  oldbalanceOrg: number;
  nameDest: string;
  oldbalanceDest: number;
  merchant_id?: string;
}

export interface EvaluateResponse {
  transaction_id: string;
  evaluation_id: string;
  timestamp_iso: string;
  risk_score: number;
  risk_band: 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';
  decision: 'APPROVED' | 'CHALLENGED' | 'REVIEW_REQUIRED' | 'DECLINED';
  action: 'APPROVE' | 'STEP_UP_CHALLENGE' | 'MANUAL_REVIEW' | 'DECLINE';
  reasons: {
    primary_code: string;
    all_codes: string[];
    narrative: string;
    causal_evidence: Record<string, any>;
  };
  engine_metadata: {
    engine_version: string;
    model_version: string;
    model_type: string;
    policy_version: string;
    operating_threshold: number;
    fallback_triggered: boolean;
    execution_latency_ms: number;
  };
}

export async function evaluateTransaction(req: EvaluateRequest): Promise<EvaluateResponse> {
  const response = await fetch('http://localhost:8000/v1/risk/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.message || 'Risk evaluation error');
  }
  return response.json();
}
```

---

## 3. Server Startup & Dev Command

To run the Risk Sentinel backend for local frontend development:
```bash
python -m uvicorn src.engine.api:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Frontend Resilience Principles

1. **Zero Client-Side Risk Logic**: The frontend must never compute risk scores, adjust thresholds, or infer actions client-side. It must strictly render the server's response.
2. **Graceful Loading & Error Toasts**: When `/v1/risk/evaluate` returns HTTP 422, display the exact validation failure (e.g. "Amount must be strictly positive").
3. **Fallback Mode Highlighting**: When `response.engine_metadata.fallback_triggered === true`, render an informational badge ("Fallback Baseline Engine Active") without alarming the user.
