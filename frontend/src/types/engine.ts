/**
 * Risk Sentinel — Frontend TypeScript Types & Contracts
 * Strictly mirrors backend schemas.py and Phase 2.11 contracts.
 */

export type TransactionType = 'TRANSFER' | 'CASH_OUT' | 'PAYMENT' | 'CASH_IN' | 'DEBIT';

export type RiskBand = 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';

export type DecisionEnum = 'APPROVED' | 'CHALLENGED' | 'REVIEW_REQUIRED' | 'DECLINED';

export type ActionEnum = 'APPROVE' | 'STEP_UP_CHALLENGE' | 'MANUAL_REVIEW' | 'DECLINE';

export interface EvaluateRequest {
  transaction_id: string;
  step: number;
  type: TransactionType;
  amount: number;
  nameOrig: string;
  oldbalanceOrg: number;
  nameDest: string;
  oldbalanceDest: number;
  merchant_id?: string;
}

export interface ReasonDetails {
  primary_code: string;
  all_codes: string[];
  narrative: string;
  causal_evidence: Record<string, any>;
}

export interface EngineMetadata {
  engine_version: string;
  model_version: string;
  model_type: string;
  policy_version: string;
  operating_threshold: number;
  fallback_triggered: boolean;
  execution_latency_ms: number;
}

export interface EvaluateResponse {
  transaction_id: string;
  evaluation_id: string;
  timestamp_iso: string;
  risk_score: number;
  risk_band: RiskBand;
  decision: DecisionEnum;
  action: ActionEnum;
  reasons: ReasonDetails;
  engine_metadata: EngineMetadata;
}

export interface HealthResponse {
  status: 'HEALTHY' | 'DEGRADED';
  engine_version: string;
  state_store_responsive: boolean;
  champion_model_sha256: string;
}

export interface AuditEvent {
  event_id: string;
  event_timestamp_utc: string;
  transaction_id: string;
  merchant_id: string;
  lineage: {
    engine_version: string;
    model_version: string;
    model_type: string;
    model_artifact_hash: string;
    policy_version: string;
    operating_threshold: number;
  };
  runtime_telemetry: {
    execution_latency_ms: number;
    state_store_latency_ms: number;
    inference_latency_ms: number;
    fallback_mode_active: boolean;
  };
  input_snapshot_masked: {
    step: number;
    type: string;
    amount: number;
    sender_masked: string;
    sender_old_balance: number;
    dest_masked: string;
    dest_old_balance: number;
  };
  causal_features_extracted: Record<string, number>;
  evaluation_result: {
    raw_model_score: number;
    risk_band: string;
    decision: string;
    action: string;
    primary_reason_code: string;
    all_reason_codes: string[];
  };
  integrity_hash: string;
}

export interface DemoFixture {
  id: string;
  title: string;
  description: string;
  request: EvaluateRequest;
  expected_decision: DecisionEnum;
  expected_action: ActionEnum;
  expected_reason: string;
  learning_takeaway: string;
  force_fallback?: boolean;
}

export interface NormalizedWebhookEvent {
  event_id: string;
  received_at_utc: string;
  source: string;
  event_type: string;
  payment_id: string;
  amount_inr: number;
  currency: string;
  method: string;
  customer_vpa?: string;
  customer_contact_masked?: string;
  merchant_id: string;
  evaluation_status: string;
  readiness_reason: string;
  missing_features: string[];
  risk_score?: number;
  decision?: string;
  action?: string;
  reasons?: ReasonDetails;
  engine_metadata?: EngineMetadata;
  audit_id?: string;
  integrity_hash: string;
  is_duplicate: boolean;
}

export interface ThresholdSensitivityRecord {
  threshold: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
  fnr: number;
  detected_fraud_amount: number;
  missed_fraud_amount: number;
  flagged_nonfraud_amount: number;
  split: string;
  is_production_threshold: boolean;
}

export interface CostSimulationPoint {
  threshold: number;
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  missed_fraud_amount: number;
  flagged_nonfraud_amount: number;
  alpha: number;
  friction_cost: number;
  total_cost: number;
  is_production_threshold: boolean;
  is_validation_cost_minimum: boolean;
}

export interface CostSimulationResponse {
  alpha: number;
  alpha_percentage: string;
  cost_equation: string;
  disclaimer: string;
  data_split: string;
  production_operating_point: CostSimulationPoint;
  simulation_table: CostSimulationPoint[];
}

export interface SOPGuidance {
  reason_code: string;
  title: string;
  objective: string;
  urgency: string;
  recommended_action: string;
  protocol_steps: string[];
  evidence_to_inspect: string[];
}

export interface InvestigationSummary {
  investigation_id: string;
  event_ref: string;
  timestamp_iso: string;
  source_provenance: 'AUDIT_LEDGER' | 'RAZORPAY_TEST_MODE' | 'DEMO_FIXTURE' | string;
  transaction_type: string;
  amount: number;
  sender_masked: string;
  dest_masked: string;
  risk_score?: number;
  risk_band: string;
  decision: string;
  action: string;
  primary_reason_code: string;
  model_version: string;
  has_audit_record: boolean;
}

export interface InvestigationDetail {
  investigation_id: string;
  event_ref: string;
  timestamp_iso: string;
  source_provenance: string;
  what_happened: {
    transaction_id?: string;
    payment_id?: string;
    event_type?: string;
    step?: number;
    channel?: string;
    method?: string;
    amount: number;
    currency?: string;
    sender_masked?: string;
    sender_old_balance?: number;
    dest_masked?: string;
    dest_old_balance?: number;
    evaluation_status?: string;
  };
  why_flagged: {
    risk_score?: number;
    risk_band: string;
    primary_reason_code: string;
    all_reason_codes: string[];
    narrative: string;
  };
  model_lineage: {
    model_name: string;
    model_type: string;
    model_sha256?: string;
    fallback_triggered?: boolean;
  };
  policy_lineage: {
    policy_version: string;
    operating_threshold: number;
    decision: string;
    action: string;
  };
  available_evidence: Record<string, any>;
  anomaly_indicators: Array<{
    signal: string;
    severity: string;
    description: string;
  }>;
  investigator_guidance: SOPGuidance;
  audit_trail: {
    audit_event_id?: string;
    chained_integrity_hash?: string;
    tamper_evident_status?: string;
  };
}

export interface CaptureGateRequest {
  payment_id: string;
  order_id?: string;
  amount_paise: number;
  currency?: string;
  status: string;
  method?: string;
  vpa?: string;
  contact?: string;
  email?: string;
  notes?: Record<string, any>;
  signature?: string;
  merchant_id?: string;
}

export interface CaptureGateResult {
  gate_event_id: string;
  timestamp_utc: string;
  payment_id: string;
  order_id?: string;
  payment_status_before: string;
  amount_inr: number;
  currency: string;
  method: string;
  customer_vpa?: string;
  customer_contact_masked?: string;
  merchant_id: string;
  risk_evaluation_status: string;
  risk_score?: number;
  decision?: string;
  action?: string;
  primary_reason_code?: string;
  reasons?: Record<string, any>;
  capture_action: 'CAPTURE_CALLED' | 'CAPTURE_SUPPRESSED' | 'CAPTURE_FAILED' | string;
  capture_status: 'CAPTURED' | 'HELD_DECLINED' | 'HELD_INSUFFICIENT_CONTEXT' | 'HELD_NON_AUTHORIZED' | 'HELD_FAIL_CLOSED' | 'HELD_DUPLICATE' | string;
  capture_api_response?: Record<string, any>;
  execution_mode: 'LIVE_RAZORPAY_TEST_MODE' | 'SIMULATED_CONTRACT_TEST_MODE' | string;
  provenance: 'RAZORPAY_TEST_MODE' | 'RAZORPAY_COMPATIBLE_TEST_MODE' | string;
  is_duplicate: boolean;
  integrity_hash: string;
  audit_event_id?: string;
}

export interface SandboxContext {
  dest_unique_orig_cnt?: number;
  sender_prev_in_tx_cnt?: number;
  is_sender_cold_start?: boolean;
}

export interface ReplayRequest {
  baseline_fixture_id?: string;
  step?: number;
  type: string;
  amount: number;
  nameOrig?: string;
  oldbalanceOrg: number;
  nameDest?: string;
  oldbalanceDest?: number;
  merchant_id?: string;
  sandbox_context?: SandboxContext;
  alpha?: number;
}

export interface ReplayEvaluation {
  model_type: string;
  operating_score: number;
  score_interpretation: string;
  risk_band: string;
  decision: string;
  action: string;
  primary_reason_code: string;
  all_reason_codes: string[];
  narrative: string;
  features: Record<string, number>;
}

export interface ReplayEconomicImpact {
  alpha: number;
  alpha_percentage: string;
  disclaimer: string;
  decision_outcome: string;
  hypothetical_fraud_exposure: number;
  hypothetical_friction_cost: number;
  economic_narrative: string;
}

export interface ReplayDelta {
  score_delta: number;
  decision_changed: boolean;
  reason_code_changed: boolean;
  baseline_decision: string;
  replay_decision: string;
  baseline_reason: string;
  replay_reason: string;
  features_diff: Record<string, { baseline: number; replay: number; delta: number }>;
}

export interface ReplayResponse {
  replay_id: string;
  timestamp_utc: string;
  provenance: string;
  baseline_fixture_id?: string;
  replay_inputs: Record<string, any>;
  replayed_evaluation: ReplayEvaluation;
  baseline_evaluation?: ReplayEvaluation;
  deltas?: ReplayDelta;
  economic_impact: ReplayEconomicImpact;
}

export interface BenchmarkConfusionMatrix {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  total_test_transactions: number;
  total_fraud_transactions: number;
  total_clean_transactions: number;
}

export interface BenchmarkSummaryResponse {
  dataset_name: string;
  dataset_file: string;
  evaluation_split: string;
  total_transactions: number;
  fraud_transactions: number;
  operating_threshold: number;
  secondary_threshold: number;
  confusion_matrix: BenchmarkConfusionMatrix;
  precision_percent: number;
  recall_percent: number;
  fraud_dollars_intercepted: number;
  fraud_dollars_missed: number;
  fraud_dollar_interception_percent: number;
  flagged_nonfraud_volume: number;
  disclaimer: string;
  threshold_provenance_note: string;
}

export type TransactionProvenance =
  | 'GENUINE_RAZORPAY_TEST_MODE'
  | 'SIMULATED_CONTRACT_TEST'
  | 'DEMO_FIXTURE'
  | 'API_DIRECT'
  | string;

export interface TransactionRecord {
  transaction_id: string;
  timestamp_iso: string;
  provenance: TransactionProvenance;
  order_id?: string;
  payment_id?: string;
  amount_inr: number;
  currency: string;
  channel_type: string;
  sender_masked: string;
  dest_masked: string;
  merchant_id: string;
  risk_score?: number;
  risk_band?: string;
  decision?: string;
  policy_action?: string;
  primary_reason_code?: string;
  reasons_narrative?: string;
  auto_response_action: 'CAPTURE_PERMITTED' | 'CAPTURE_SUPPRESSED' | 'NOT_APPLICABLE' | 'CAPTURE_FAILED' | string;
  auto_response_status: 'CAPTURED' | 'HELD_DECLINED' | 'HELD_REVIEW_REQUIRED' | 'HELD_INSUFFICIENT_CONTEXT' | 'HELD_NON_AUTHORIZED' | 'PENDING_REVIEW' | 'DIRECT_EVALUATION' | string;
  auto_response_details?: Record<string, any>;
  model_version: string;
  policy_version: string;
  audit_event_id?: string;
  integrity_hash: string;
}

export interface TransactionSummary {
  total_transactions: number;
  total_volume_inr: number;
  by_provenance: Record<string, number>;
  by_decision: Record<string, number>;
  by_auto_response: Record<string, number>;
}

export interface RazorpayConnectionStatus {
  connected: boolean;
  is_live_credentials: boolean;
  mode: string;
  key_id_masked?: string;
  has_secret: boolean;
  has_webhook_secret: boolean;
  verified_at_utc?: string;
  last_error?: string;
}

export interface RazorpayConnectRequest {
  key_id: string;
  key_secret: string;
  webhook_secret?: string;
}

export interface CreateOrderRequest {
  amount_paise: number;
  currency?: string;
  receipt?: string;
  notes?: Record<string, any>;
}

export interface CreateOrderResponse {
  order_id: string;
  amount_paise: number;
  amount_inr: number;
  currency: string;
  payment_capture: number;
  status: string;
  receipt?: string;
  created_at: number;
  is_simulated: boolean;
  key_id?: string;
  notes?: Record<string, any>;
}

export interface ProcessCheckoutRequest {
  order_id: string;
  payment_id: string;
  signature: string;
  amount_paise?: number;
  notes?: Record<string, any>;
  merchant_id?: string;
}

export interface LiveVerificationResult {
  payment_id: string;
  order_id?: string;
  live_payment_found: boolean;
  live_status?: string;
  live_captured?: boolean;
  live_amount_inr?: number;
  live_method?: string;
  local_record_found: boolean;
  local_decision?: string;
  local_risk_score?: number;
  local_auto_response?: string;
  discrepancy_detected: boolean;
  discrepancy_details?: string;
  verified_at_utc: string;
  raw_razorpay_response?: Record<string, any>;
}

export interface SelfTestItem {
  step: number;
  name: string;
  passed: boolean;
  category: 'LIVE_PROVEN' | 'CONTRACT_PROVEN' | 'LOCAL_POLICY_INVARIANT_PROVEN' | 'NOT_EXECUTED' | string;
  details: string;
  latency_ms: number;
}

export interface SelfTestResponse {
  all_passed: boolean;
  total_tests: number;
  passed_tests: number;
  execution_mode: string;
  tested_at_utc: string;
  tests: SelfTestItem[];
}

export interface WebhookConfigureRequest {
  webhook_secret: string;
}

export interface RazorpayWebhookStatus {
  webhook_configured: boolean;
  webhook_secret_masked?: string;
  endpoint_url: string;
  events_received_count: number;
  last_event_at_utc?: string;
  last_event_id?: string;
  last_event_status?: string;
}

export interface WebhookContractTestRequest {
  scenario: 'DRAIN_ATTEMPT' | 'BENIGN_PAYMENT' | 'RAW_GATEWAY' | string;
  amount_inr?: number;
  payment_id?: string;
}

export interface WebhookContractTestResponse {
  success: boolean;
  signature_verified: boolean;
  scenario: string;
  generated_event: Record<string, any>;
  normalized_event: NormalizedWebhookEvent;
  auto_response_action: string;
  provenance: string;
  tested_at_utc: string;
}



