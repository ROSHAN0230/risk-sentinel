/**
 * Risk Sentinel — API Client Service
 * Connects to FastAPI backend (/v1/risk/evaluate, /v1/health, /v1/audit/events, /v1/model/info)
 */

import {
  EvaluateRequest,
  EvaluateResponse,
  HealthResponse,
  AuditEvent,
  DemoFixture,
  ThresholdSensitivityRecord,
  CostSimulationResponse,
  InvestigationSummary,
  InvestigationDetail,
  CaptureGateRequest,
  CaptureGateResult,
  ReplayRequest,
  ReplayResponse,
  BenchmarkSummaryResponse,
  TransactionRecord,
  TransactionSummary
} from '../types/engine';

const API_BASE = '/v1';

export const DEMO_FIXTURES: DemoFixture[] = [
  {
    id: 'DEMO-01',
    title: 'Normal Consumer Payment',
    description: 'Legitimate consumer buying goods via PAYMENT channel. Fast-track empirical bypass.',
    request: {
      transaction_id: 'demo-tx-001-payment',
      step: 450,
      type: 'PAYMENT',
      amount: 84.50,
      nameOrig: 'C_ALICE_01',
      oldbalanceOrg: 1200.00,
      nameDest: 'M_BOOKSTORE_01',
      oldbalanceDest: 0.00
    },
    expected_decision: 'APPROVED',
    expected_action: 'APPROVE',
    expected_reason: 'RC_BENIGN_BASELINE',
    learning_takeaway: 'Proves frictionless approval on low-risk commerce in <2ms.'
  },
  {
    id: 'DEMO-02',
    title: 'Suspicious Severe Liquidity Outflow',
    description: 'High-value transfer draining 99.37% of available balance ($976,662.30) to novel recipient.',
    request: {
      transaction_id: 'demo-tx-002-suspicious',
      step: 324,
      type: 'TRANSFER',
      amount: 976662.30,
      nameOrig: 'C1959219454',
      oldbalanceOrg: 982857.46,
      nameDest: 'C2061756973',
      oldbalanceDest: 2453029.29
    },
    expected_decision: 'REVIEW_REQUIRED',
    expected_action: 'MANUAL_REVIEW',
    expected_reason: 'RC_SEVERE_LIQUIDITY_DRAIN',
    learning_takeaway: 'Demonstrates decoupled medium-risk policy queue (score 0.9830 in [0.90, 0.99)).'
  },
  {
    id: 'DEMO-03',
    title: 'Critical Fraud — 100% Balance Drain',
    description: 'Compromised account attempting exact 100% balance drain via TRANSFER channel.',
    request: {
      transaction_id: 'demo-tx-003-drain',
      step: 452,
      type: 'TRANSFER',
      amount: 284100.50,
      nameOrig: 'C_VICTIM_03',
      oldbalanceOrg: 284100.50,
      nameDest: 'C_MULE_03',
      oldbalanceDest: 0.00
    },
    expected_decision: 'DECLINED',
    expected_action: 'DECLINE',
    expected_reason: 'RC_EXACT_BALANCE_DRAIN',
    learning_takeaway: 'High-precision automated decline intercepting 100% of drain volume.'
  },
  {
    id: 'DEMO-04',
    title: 'Benign Cold-Start Account',
    description: 'Brand new account (first-ever transfer) sending normal 5% balance amount.',
    request: {
      transaction_id: 'demo-tx-004-coldstart',
      step: 453,
      type: 'TRANSFER',
      amount: 50.00,
      nameOrig: 'C_FRESH_USER_04',
      oldbalanceOrg: 1000.00,
      nameDest: 'C_DEST_04',
      oldbalanceDest: 200.00
    },
    expected_decision: 'APPROVED',
    expected_action: 'APPROVE',
    expected_reason: 'RC_BENIGN_BASELINE',
    learning_takeaway: 'Verifies FROZEN #010: Cold-start is context, not evidence of fraud.'
  },
  {
    id: 'DEMO-05',
    title: 'State Outage Fallback Mode',
    description: 'Simulated Redis/cache outage. Automatically trips circuit breaker to Model A.',
    request: {
      transaction_id: 'demo-tx-005-fallback',
      step: 454,
      type: 'TRANSFER',
      amount: 190000.00,
      nameOrig: 'C_FALLBACK_USER_05',
      oldbalanceOrg: 190000.00,
      nameDest: 'C_FALLBACK_DEST_05',
      oldbalanceDest: 0.00
    },
    expected_decision: 'DECLINED',
    expected_action: 'DECLINE',
    expected_reason: 'RC_EXACT_BALANCE_DRAIN',
    learning_takeaway: 'Demonstrates zero-downtime resilience with Model A Causal Baseline.',
    force_fallback: true
  },
  {
    id: 'DEMO-06',
    title: 'Cryptographic Model Tamper Defense',
    description: 'Startup check: SHA-256 verification against engine manifest.',
    request: {
      transaction_id: 'demo-tx-006-tamper',
      step: 455,
      type: 'TRANSFER',
      amount: 100.00,
      nameOrig: 'C_TAMPER_06',
      oldbalanceOrg: 500.00,
      nameDest: 'C_DEST_06',
      oldbalanceDest: 0.00
    },
    expected_decision: 'APPROVED',
    expected_action: 'APPROVE',
    expected_reason: 'RC_BENIGN_BASELINE',
    learning_takeaway: 'Proves binary integrity check prevents execution of tampered weights.'
  },
  {
    id: 'DEMO-07',
    title: 'Causal Explanation & Evidence',
    description: 'Inspection of exact reason codes, narrative, and numeric evidence dictionary.',
    request: {
      transaction_id: 'demo-tx-007-explanation',
      step: 456,
      type: 'CASH_OUT',
      amount: 99000.00,
      nameOrig: 'C_DRAIN_07',
      oldbalanceOrg: 99000.00,
      nameDest: 'C_DEST_07',
      oldbalanceDest: 500.00
    },
    expected_decision: 'DECLINED',
    expected_action: 'DECLINE',
    expected_reason: 'RC_EXACT_BALANCE_DRAIN',
    learning_takeaway: 'Audit-ready, deterministic causal explanations for compliance officers.'
  },
  {
    id: 'DEMO-08',
    title: 'Cryptographic Audit Trail',
    description: 'Verifying tamper-evident audit log with PII masking and SHA-256 block hash chaining.',
    request: {
      transaction_id: 'demo-tx-008-audit',
      step: 457,
      type: 'TRANSFER',
      amount: 120.00,
      nameOrig: 'C192837465',
      oldbalanceOrg: 2000.00,
      nameDest: 'C987654321',
      oldbalanceDest: 100.00
    },
    expected_decision: 'APPROVED',
    expected_action: 'APPROVE',
    expected_reason: 'RC_BENIGN_BASELINE',
    learning_takeaway: 'Proves mathematical immutability and anti-repudiation.'
  },
  {
    id: 'DEMO-09',
    title: 'Financial Cost & Threshold Tradeoff',
    description: 'Demonstrating why threshold 0.990 minimizes financial loss ($64k vs $12.97M).',
    request: {
      transaction_id: 'demo-tx-009-cost',
      step: 458,
      type: 'TRANSFER',
      amount: 500000.00,
      nameOrig: 'C_COST_09',
      oldbalanceOrg: 500000.00,
      nameDest: 'C_DEST_09',
      oldbalanceDest: 0.00
    },
    expected_decision: 'DECLINED',
    expected_action: 'DECLINE',
    expected_reason: 'RC_EXACT_BALANCE_DRAIN',
    learning_takeaway: 'Shows how cost-sensitive thresholding saves millions in false positives.'
  }
];

export async function evaluateTransaction(req: EvaluateRequest): Promise<EvaluateResponse> {
  const response = await fetch(`${API_BASE}/risk/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errJson = await response.json();
      errorMsg = errJson.message || errJson.detail || errorMsg;
    } catch (_) {}
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return response.json();
}

export async function getModelInfo(): Promise<Record<string, any>> {
  const response = await fetch(`${API_BASE}/model/info`);
  if (!response.ok) {
    throw new Error(`Failed to fetch model info (${response.status})`);
  }
  return response.json();
}

export async function getAuditEvents(limit: number = 50): Promise<AuditEvent[]> {
  const response = await fetch(`${API_BASE}/audit/events?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch audit events (${response.status})`);
  }
  return response.json();
}

export async function getWebhookEvents(limit: number = 50): Promise<any[]> {
  const response = await fetch(`${API_BASE}/webhooks/events?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch webhook events (${response.status})`);
  }
  return response.json();
}

export async function postRazorpayWebhook(payload: Record<string, any>, signature?: string): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  if (signature) {
    headers['X-Razorpay-Signature'] = signature;
  }
  const response = await fetch(`${API_BASE}/webhooks/razorpay`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });
  return response.json();
}

export async function getThresholdSensitivity(): Promise<ThresholdSensitivityRecord[]> {
  const response = await fetch(`${API_BASE}/analytics/threshold-sensitivity`);
  if (!response.ok) {
    throw new Error(`Failed to fetch threshold sensitivity (${response.status})`);
  }
  return response.json();
}

export async function getCostSimulation(alpha: number = 0.01): Promise<CostSimulationResponse> {
  const response = await fetch(`${API_BASE}/analytics/cost-simulation?alpha=${alpha}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch cost simulation (${response.status})`);
  }
  return response.json();
}

export async function getInvestigations(params?: {
  limit?: number;
  band?: string;
  provenance?: string;
}): Promise<InvestigationSummary[]> {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.band) query.set('band', params.band);
  if (params?.provenance) query.set('provenance', params.provenance);

  const qs = query.toString() ? `?${query.toString()}` : '';
  const response = await fetch(`${API_BASE}/investigations${qs}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch investigations (${response.status})`);
  }
  return response.json();
}

export async function getInvestigationDetail(investigationId: string): Promise<InvestigationDetail> {
  const response = await fetch(`${API_BASE}/investigations/${encodeURIComponent(investigationId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch investigation ${investigationId} (${response.status})`);
  }
  return response.json();
}

export async function evaluateAndCaptureGate(request: CaptureGateRequest): Promise<CaptureGateResult> {
  const response = await fetch(`${API_BASE}/gate/evaluate-and-capture`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(`Failed to evaluate and capture (${response.status})`);
  }
  return response.json();
}

export async function getCaptureGateEvents(limit: number = 50): Promise<CaptureGateResult[]> {
  const response = await fetch(`${API_BASE}/gate/events?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch capture gate events (${response.status})`);
  }
  return response.json();
}

export async function evaluateReplay(request: ReplayRequest): Promise<ReplayResponse> {
  const response = await fetch(`${API_BASE}/replay/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(`Failed to evaluate replay (${response.status})`);
  }
  return response.json();
}

export async function getBenchmarkSummary(): Promise<BenchmarkSummaryResponse> {
  const response = await fetch(`${API_BASE}/analytics/benchmark-summary`);
  if (!response.ok) {
    throw new Error(`Failed to fetch benchmark summary (${response.status})`);
  }
  return response.json();
}

export async function getTransactions(params?: {
  limit?: number;
  provenance?: string;
  decision?: string;
}): Promise<TransactionRecord[]> {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.provenance) query.set('provenance', params.provenance);
  if (params?.decision) query.set('decision', params.decision);

  const qs = query.toString() ? `?${query.toString()}` : '';
  const response = await fetch(`${API_BASE}/transactions${qs}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch transactions (${response.status})`);
  }
  return response.json();
}

export async function getTransactionSummary(): Promise<TransactionSummary> {
  const response = await fetch(`${API_BASE}/transactions/summary`);
  if (!response.ok) {
    throw new Error(`Failed to fetch transaction summary (${response.status})`);
  }
  return response.json();
}

export async function getTransactionById(transactionId: string): Promise<TransactionRecord> {
  const response = await fetch(`${API_BASE}/transactions/${encodeURIComponent(transactionId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch transaction ${transactionId} (${response.status})`);
  }
  return response.json();
}




