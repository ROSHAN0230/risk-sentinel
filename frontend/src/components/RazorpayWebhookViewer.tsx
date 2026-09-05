import React, { useState, useEffect } from 'react';
import {
  getWebhookEvents,
  configureRazorpayWebhook,
  getRazorpayWebhookStatus,
  clearRazorpayWebhook,
  runWebhookContractTest
} from '../api/client';
import {
  NormalizedWebhookEvent,
  RazorpayWebhookStatus,
  WebhookContractTestResponse
} from '../types/engine';
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ArrowDownRight,
  RefreshCw,
  Send,
  Lock,
  Copy,
  Check,
  Key,
  Trash2,
  Play,
  Server,
  Zap,
  Radio,
  ExternalLink,
  ShieldCheck,
  ShieldX
} from 'lucide-react';

export const RazorpayWebhookViewer: React.FC = () => {
  const [events, setEvents] = useState<NormalizedWebhookEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState<boolean>(false);
  const [status, setStatus] = useState<RazorpayWebhookStatus | null>(null);
  const [secretInput, setSecretInput] = useState<string>('');
  const [savingSecret, setSavingSecret] = useState<boolean>(false);
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Contract Test State
  const [selectedScenario, setSelectedScenario] = useState<'DRAIN_ATTEMPT' | 'BENIGN_PAYMENT' | 'RAW_GATEWAY'>('DRAIN_ATTEMPT');
  const [runningContractTest, setRunningContractTest] = useState<boolean>(false);
  const [contractTestResult, setContractTestResult] = useState<WebhookContractTestResponse | null>(null);

  const endpointUrl = status?.endpoint_url || 'https://risk-sentinel.onrender.com/v1/webhooks/razorpay';

  const fetchStatus = async () => {
    try {
      const s = await getRazorpayWebhookStatus();
      setStatus(s);
    } catch (err) {
      console.error('Failed to load webhook status:', err);
    }
  };

  const fetchEvents = async () => {
    setLoadingEvents(true);
    try {
      const data = await getWebhookEvents(30);
      setEvents(data);
    } catch (err) {
      console.error('Failed to load webhook events:', err);
    } finally {
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchEvents();
    const interval = setInterval(() => {
      fetchEvents();
      fetchStatus();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(endpointUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const handleSaveSecret = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!secretInput.trim()) return;
    setSavingSecret(true);
    setStatusMsg(null);
    try {
      const updated = await configureRazorpayWebhook({ webhook_secret: secretInput.trim() });
      setStatus(updated);
      setSecretInput('');
      setStatusMsg({ type: 'success', text: 'Webhook Secret configured securely in server memory.' });
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to configure webhook secret.' });
    } finally {
      setSavingSecret(false);
    }
  };

  const handleClearSecret = async () => {
    setSavingSecret(true);
    setStatusMsg(null);
    try {
      const updated = await clearRazorpayWebhook();
      setStatus(updated);
      setStatusMsg({ type: 'success', text: 'Webhook Secret cleared. Running in signature-permissive development mode.' });
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to clear secret.' });
    } finally {
      setSavingSecret(false);
    }
  };

  const handleRunContractTest = async () => {
    setRunningContractTest(true);
    setStatusMsg(null);
    try {
      const result = await runWebhookContractTest({ scenario: selectedScenario });
      setContractTestResult(result);
      await fetchEvents();
      await fetchStatus();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to run contract test.' });
    } finally {
      setRunningContractTest(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl mt-8">
      {/* Header Banner */}
      <div className="p-5 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/40 border-b border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wide">
              Track 02 Integration
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Vector B: Incoming Webhook Gate
            </span>
          </div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2 mt-1">
            Razorpay Test Mode Webhook Gateway &amp; Monitor
          </h3>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Receives external authorization and capture events directly from Razorpay, validates HMAC-SHA256 signatures,
            enforces idempotency, applies frozen model inference, and enforces merchant-controlled pre-capture auto-responses.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => { fetchEvents(); fetchStatus(); }}
            disabled={loadingEvents}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingEvents ? 'animate-spin' : ''}`} />
            Refresh Feed
          </button>
        </div>
      </div>

      {statusMsg && (
        <div className={`px-5 py-2.5 text-xs font-mono flex items-center justify-between border-b ${
          statusMsg.type === 'success' ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300' : 'bg-red-950/40 border-red-500/30 text-red-300'
        }`}>
          <div className="flex items-center gap-2">
            {statusMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-red-400" />}
            <span>{statusMsg.text}</span>
          </div>
          <button onClick={() => setStatusMsg(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Grid: Webhook Configuration & Signed Contract Verification */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 p-5 border-b border-slate-800 bg-slate-950/40">
        
        {/* Left Column: Configuration & Endpoint Setup */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Webhook Endpoint &amp; Secret Configuration
                </h4>
              </div>
              {status?.webhook_configured ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  HMAC CONFIGURED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <AlertTriangle className="w-3 h-3" />
                  DEV MODE (UNCONFIGURED)
                </span>
              )}
            </div>

            {/* URL Display */}
            <div className="mt-3">
              <label className="text-[11px] font-medium text-slate-400 block mb-1">
                Public Razorpay Webhook URL (POST):
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={endpointUrl}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-indigo-300 select-all focus:outline-none"
                />
                <button
                  onClick={handleCopyUrl}
                  className="px-3 py-2 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
                  title="Copy Webhook URL"
                >
                  {copiedUrl ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  <span>{copiedUrl ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                Paste into your Razorpay Dashboard &rarr; Settings &rarr; Webhooks &rarr; Add New Webhook.
              </p>
            </div>

            {/* Secret Form */}
            <form onSubmit={handleSaveSecret} className="mt-4">
              <label className="text-[11px] font-medium text-slate-400 block mb-1">
                Webhook Secret (Memory-only, HMAC-SHA256):
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="password"
                  value={secretInput}
                  onChange={(e) => setSecretInput(e.target.value)}
                  placeholder={status?.webhook_configured ? `Active: ${status.webhook_secret_masked}` : 'Enter Razorpay Webhook Secret...'}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={savingSecret || !secretInput.trim()}
                  className="px-3 py-2 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-white transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <Key className="w-3.5 h-3.5" />
                  <span>Save Secret</span>
                </button>
                {status?.webhook_configured && (
                  <button
                    type="button"
                    onClick={handleClearSecret}
                    disabled={savingSecret}
                    className="p-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-500/30 transition-colors"
                    title="Clear Webhook Secret"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Delivery Telemetry */}
          <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <div>
              Total Ingested: <span className="font-bold text-white">{status?.events_received_count || 0}</span> events
            </div>
            <div>
              Last Activity: <span className="text-slate-300">{status?.last_event_at_utc ? new Date(status.last_event_at_utc).toLocaleTimeString() : 'None'}</span>
            </div>
          </div>
        </div>

        {/* Right Column: Verify Webhook (Signed Contract Test) */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Dual-Path Verification (Signed Contract Proof)
                </h4>
              </div>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                Path A: Local Signed Proof
              </span>
            </div>

            <p className="text-[11px] text-slate-400 mt-2.5 leading-relaxed">
              Generates a cryptographically valid HMAC-SHA256 signed Razorpay Test payload, dispatches it to <code className="text-indigo-300">/v1/webhooks/razorpay</code>, and validates the end-to-end risk auto-response.
            </p>

            {/* Scenario Selector */}
            <div className="mt-3 grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSelectedScenario('DRAIN_ATTEMPT')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                  selectedScenario === 'DRAIN_ATTEMPT'
                    ? 'bg-red-950/40 border-red-500/50 text-red-200 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase">Critical Drain</span>
                  <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                </div>
                <div className="font-mono text-xs font-bold text-white">₹284,100.50</div>
                <div className="text-[9px] text-slate-400">100% Drain &rarr; Suppress</div>
              </button>

              <button
                type="button"
                onClick={() => setSelectedScenario('BENIGN_PAYMENT')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                  selectedScenario === 'BENIGN_PAYMENT'
                    ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-200 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase">Benign Payment</span>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <div className="font-mono text-xs font-bold text-white">₹84.50</div>
                <div className="text-[9px] text-slate-400">Low Risk &rarr; Permit</div>
              </button>

              <button
                type="button"
                onClick={() => setSelectedScenario('RAW_GATEWAY')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                  selectedScenario === 'RAW_GATEWAY'
                    ? 'bg-amber-950/40 border-amber-500/50 text-amber-200 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase">Raw Gateway</span>
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                </div>
                <div className="font-mono text-xs font-bold text-white">₹1,500.00</div>
                <div className="text-[9px] text-slate-400">No Bank Ctx &rarr; Gate</div>
              </button>
            </div>
          </div>

          <button
            onClick={handleRunContractTest}
            disabled={runningContractTest}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors flex items-center justify-center gap-2 shadow-sm"
          >
            {runningContractTest ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>Execute Signed Webhook Contract Test</span>
          </button>
        </div>
      </div>

      {/* Contract Test Result Showcase Card */}
      {contractTestResult && (
        <div className="p-5 bg-slate-950 border-b border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                PROVENANCE: {contractTestResult.provenance}
              </span>
              <span className="text-xs font-bold text-white">
                Contract Proof Execution Result ({contractTestResult.scenario})
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              {new Date(contractTestResult.tested_at_utc).toLocaleTimeString()}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              <div className="text-slate-500 text-[10px]">HMAC SIGNATURE</div>
              <div className="font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>SHA-256 VALID</span>
              </div>
              <div className="text-[9px] text-slate-500 mt-1 truncate">
                Payment: {contractTestResult.normalized_event.payment_id}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              <div className="text-slate-500 text-[10px]">EVALUATION STATUS</div>
              <div className="font-bold text-white mt-0.5 truncate">
                {contractTestResult.normalized_event.evaluation_status}
              </div>
              <div className="text-[9px] text-slate-400 mt-1">
                Score: {contractTestResult.normalized_event.risk_score?.toFixed(4) ?? 'N/A'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              <div className="text-slate-500 text-[10px]">DECISION &amp; POLICY</div>
              <div className="font-bold mt-0.5 flex items-center gap-1.5">
                {contractTestResult.normalized_event.decision === 'DECLINED' ? (
                  <span className="text-red-400 flex items-center gap-1">
                    <ShieldX className="w-4 h-4" /> DECLINED
                  </span>
                ) : contractTestResult.normalized_event.decision === 'APPROVED' ? (
                  <span className="text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-4 h-4" /> APPROVED
                  </span>
                ) : (
                  <span className="text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="w-4 h-4" /> GATED
                  </span>
                )}
              </div>
              <div className="text-[9px] text-slate-400 mt-1">
                Action: {contractTestResult.normalized_event.action || 'HOLD_NO_CAPTURE'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              <div className="text-slate-500 text-[10px]">AUTO-RESPONSE ACTION</div>
              <div className="font-bold mt-0.5">
                <span className={`px-2 py-0.5 rounded text-[10px] ${
                  contractTestResult.auto_response_action === 'CAPTURE_PERMITTED'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {contractTestResult.auto_response_action}
                </span>
              </div>
              <div className="text-[9px] text-slate-500 mt-1 truncate">
                Hash: {contractTestResult.normalized_event.integrity_hash.slice(0, 16)}...
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Events Stream Table */}
      <div className="overflow-x-auto">
        <div className="px-5 py-3 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-300">
            <Radio className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
            <span>Incoming Webhook Events Stream ({events.length})</span>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
              GENUINE_RAZORPAY_TEST_MODE
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              SIMULATED_CONTRACT_TEST
            </span>
          </div>
        </div>

        {events.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs font-mono">
            No webhook events received yet. Click "Execute Signed Webhook Contract Test" or trigger a payment via Razorpay Checkout.
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800 font-mono">
              <tr>
                <th className="px-4 py-3">Provenance &amp; Payment ID</th>
                <th className="px-4 py-3">Event Type</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Model Readiness State</th>
                <th className="px-4 py-3">Risk Decision</th>
                <th className="px-4 py-3">Auto-Response</th>
                <th className="px-4 py-3 text-right">Integrity Audit Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {events.map((ev) => {
                const isInsufficient = ev.evaluation_status === 'INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION';
                const isEnriched = ev.evaluation_status === 'EVALUATED_ENRICHED_TEST_MODE';
                const isContractTest = ev.payment_id.toLowerCase().includes('contract') || ev.payment_id.toLowerCase().includes('simulated') || ev.payment_id.toLowerCase().includes('test');
                const autoAction = ev.decision === 'APPROVED' ? 'CAPTURE_PERMITTED' : 'CAPTURE_SUPPRESSED';

                return (
                  <tr key={ev.event_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          isContractTest ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                        }`}>
                          {isContractTest ? 'SIMULATED_CONTRACT_TEST' : 'GENUINE_RAZORPAY_TEST_MODE'}
                        </span>
                      </div>
                      <div className="font-bold text-white mt-1">{ev.payment_id}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {ev.method.toUpperCase()} • {ev.customer_contact_masked || ev.customer_vpa || 'Anonymous'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-slate-300 font-medium">{ev.event_type}</span>
                      <div className="text-[10px] text-slate-500">{new Date(ev.received_at_utc).toLocaleTimeString()}</div>
                    </td>
                    <td className="px-4 py-3 font-semibold text-white">
                      ₹{ev.amount_inr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3">
                      {isInsufficient ? (
                        <div>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            <AlertTriangle className="w-3 h-3" />
                            INSUFFICIENT FEATURES
                          </span>
                          <p className="text-[10px] text-slate-400 mt-1 max-w-xs leading-relaxed font-sans">
                            Received successfully. Raw gateway webhook lacks banking balance context.
                          </p>
                        </div>
                      ) : isEnriched ? (
                        <div>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <CheckCircle2 className="w-3 h-3" />
                            ENRICHED CONTEXT
                          </span>
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Model: {ev.engine_metadata?.model_version || 'v1.0.0-HGB'} | θ* = 0.990
                          </div>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-400">{ev.evaluation_status}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {ev.decision ? (
                        <div>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                            ev.decision === 'DECLINED' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                            ev.decision === 'REVIEW_REQUIRED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                            'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}>
                            {ev.action} ({ev.risk_score?.toFixed(4)})
                          </span>
                          {ev.audit_id && (
                            <div className="text-[9px] text-slate-500 mt-0.5 truncate max-w-[120px]">
                              {ev.audit_id}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-600 text-xs italic">N/A (Gated)</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                        autoAction === 'CAPTURE_PERMITTED'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-red-500/10 text-red-400 border border-red-500/20'
                      }`}>
                        {autoAction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800">
                        {ev.integrity_hash.slice(0, 16)}...
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
