import React, { useState, useEffect } from 'react';
import {
  EvaluateResponse,
  InvestigationSummary,
  InvestigationDetail
} from '../types/engine';
import { getInvestigations, getInvestigationDetail } from '../api/client';
import { RiskScoreGauge } from '../components/RiskScoreGauge';
import { ReasonCodeCard } from '../components/ReasonCodeCard';
import { CausalEvidenceGrid } from '../components/CausalEvidenceGrid';
import { EngineTelemetry } from '../components/EngineTelemetry';
import { DecisionBadge } from '../components/DecisionBadge';
import { RiskBandBadge } from '../components/RiskBandBadge';
import { DataSourceBadge } from '../components/DataSourceBadge';
import {
  ArrowLeft,
  Search,
  RefreshCw,
  Shield,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Clock,
  Cpu,
  Lock,
  BookOpen,
  Filter,
  CheckSquare,
  AlertCircle
} from 'lucide-react';

interface Props {
  evaluation: EvaluateResponse | null;
  onBack: () => void;
}

export const InspectorPage: React.FC<Props> = ({ evaluation, onBack }) => {
  const [queue, setQueue] = useState<InvestigationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('investigation') || evaluation?.transaction_id || null;
  });
  const [detail, setDetail] = useState<InvestigationDetail | null>(null);
  const [isLoadingQueue, setIsLoadingQueue] = useState<boolean>(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [provenanceFilter, setProvenanceFilter] = useState<string>('ALL');
  const [bandFilter, setBandFilter] = useState<string>('ALL');

  // Load Investigation Queue
  const fetchQueue = async () => {
    setIsLoadingQueue(true);
    setErrorMsg(null);
    try {
      const data = await getInvestigations({ limit: 50 });
      setQueue(data);
      // If no item selected yet, select the first high-risk event or first item
      if (!selectedId && data.length > 0) {
        const defaultPick = data.find((d) => d.risk_band === 'HIGH_RISK') || data[0];
        handleSelectInvestigation(defaultPick.investigation_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch investigation queue');
    } finally {
      setIsLoadingQueue(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  // Sync when prop evaluation changes
  useEffect(() => {
    if (evaluation) {
      setSelectedId(evaluation.transaction_id);
      loadDetail(evaluation.transaction_id);
    }
  }, [evaluation]);

  // Load Investigation Detail Dossier
  const loadDetail = async (id: string) => {
    setIsLoadingDetail(true);
    try {
      const d = await getInvestigationDetail(id);
      setDetail(d);
      // Update browser URL query param for deep-linking
      const url = new URL(window.location.href);
      url.searchParams.set('investigation', id);
      window.history.replaceState({}, '', url.toString());
    } catch (err: any) {
      console.error('Failed to load investigation detail:', err);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleSelectInvestigation = (id: string) => {
    setSelectedId(id);
    loadDetail(id);
  };

  // Filtered Queue
  const filteredQueue = queue.filter((item) => {
    if (provenanceFilter !== 'ALL' && item.source_provenance !== provenanceFilter) return false;
    if (bandFilter !== 'ALL' && item.risk_band !== bandFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesRef = item.event_ref.toLowerCase().includes(q);
      const matchesSender = item.sender_masked.toLowerCase().includes(q);
      const matchesReason = item.primary_reason_code.toLowerCase().includes(q);
      if (!matchesRef && !matchesSender && !matchesReason) return false;
    }
    return true;
  });

  return (
    <div className="flex flex-col gap-6 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-white transition-colors bg-slate-800/80 px-2.5 py-1.5 rounded-lg border border-slate-700"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Live Stream</span>
          </button>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              Investigation Workspace
            </h1>
            <p className="text-xs text-slate-400 font-mono">
              Observe → Detect → Explain → Investigate → Decide → Record
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
            FROZEN POLICY: θ* = 0.990
          </span>
          <button
            onClick={fetchQueue}
            disabled={isLoadingQueue}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-mono transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingQueue ? 'animate-spin' : ''}`} />
            <span>Refresh Queue</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-500/40 text-red-300 text-xs font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 2-Panel Master Investigation Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANEL: Investigation Queue (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-blue-400" />
              Investigation Queue ({filteredQueue.length})
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Read-Only</span>
          </div>

          {/* Search Bar */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search by ID, account, reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>

          {/* Filter Chips */}
          <div className="flex flex-wrap gap-1 text-[10px] font-mono">
            {['ALL', 'AUDIT_LEDGER', 'RAZORPAY_TEST_MODE', 'DEMO_FIXTURE'].map((prov) => (
              <button
                key={prov}
                onClick={() => setProvenanceFilter(prov)}
                className={`px-2 py-0.5 rounded transition-all ${
                  provenanceFilter === prov
                    ? 'bg-blue-600 text-white font-bold'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {prov === 'ALL' ? 'All Sources' : prov === 'AUDIT_LEDGER' ? 'Audit Record' : prov === 'RAZORPAY_TEST_MODE' ? 'Test Mode' : 'Demo Fixture'}
              </button>
            ))}
          </div>

          <div className="flex gap-1 text-[10px] font-mono">
            {['ALL', 'HIGH_RISK', 'MEDIUM_RISK', 'LOW_RISK'].map((band) => (
              <button
                key={band}
                onClick={() => setBandFilter(band)}
                className={`px-2 py-0.5 rounded transition-all ${
                  bandFilter === band
                    ? 'bg-slate-700 text-white font-bold border border-slate-600'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {band === 'ALL' ? 'All Tiers' : band.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Queue Scroll List */}
          <div className="flex flex-col gap-2 max-h-[700px] overflow-y-auto pr-1">
            {filteredQueue.length === 0 ? (
              <div className="p-6 text-center text-xs font-mono text-slate-500">
                No risk events match current filters.
              </div>
            ) : (
              filteredQueue.map((item) => {
                const isSelected = selectedId === item.investigation_id || selectedId === item.event_ref;
                const isHigh = item.risk_band === 'HIGH_RISK';
                const isMed = item.risk_band === 'MEDIUM_RISK';

                return (
                  <div
                    key={item.investigation_id}
                    onClick={() => handleSelectInvestigation(item.investigation_id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-blue-950/40 border-blue-500 shadow-sm text-white'
                        : 'bg-slate-950/60 hover:bg-slate-800/40 border-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono">
                      <span className={`px-1.5 py-0.2 rounded font-semibold ${
                        item.source_provenance === 'AUDIT_LEDGER'
                          ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                          : item.source_provenance === 'RAZORPAY_TEST_MODE'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                      }`}>
                        {item.source_provenance === 'AUDIT_LEDGER' ? 'AUDIT RECORD' : item.source_provenance === 'RAZORPAY_TEST_MODE' ? 'TEST MODE' : 'DEMO FIXTURE'}
                      </span>
                      <span className="text-slate-500">{item.transaction_type}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-200 truncate">
                        {item.event_ref}
                      </span>
                      <span className="font-mono text-xs font-semibold text-slate-300">
                        ${item.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-slate-400">{item.sender_masked}</span>
                      <div className="flex items-center gap-1.5">
                        {item.risk_score !== null && item.risk_score !== undefined && (
                          <span className={`font-bold ${isHigh ? 'text-red-400' : isMed ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {item.risk_score.toFixed(4)}
                          </span>
                        )}
                        <span className={`px-1 rounded text-[9px] font-bold ${
                          item.decision === 'DECLINED' || item.decision === 'DECLINE'
                            ? 'bg-red-500/20 text-red-300'
                            : item.decision === 'REVIEW_REQUIRED' || item.decision === 'MANUAL_REVIEW' || item.decision === 'CHALLENGED'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}>
                          {item.decision}
                        </span>
                      </div>
                    </div>

                    <div className="text-[10px] font-mono text-slate-400 truncate bg-slate-900/80 px-1.5 py-0.5 rounded border border-slate-800/60">
                      {item.primary_reason_code}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT PANEL: Investigation Dossier (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {isLoadingDetail ? (
            <div className="p-12 rounded-xl bg-slate-900 border border-slate-800 text-center font-mono text-sm text-slate-400">
              Loading investigation dossier...
            </div>
          ) : !detail ? (
            <div className="p-12 rounded-xl bg-slate-900 border border-slate-800 text-center flex flex-col items-center gap-3">
              <FileText className="w-10 h-10 text-slate-600" />
              <h3 className="text-base font-bold text-white">Select a Risk Event from the Queue</h3>
              <p className="text-xs text-slate-400 font-mono max-w-md">
                Click on any live audit record, Razorpay Test Mode event, or demo fixture to inspect why it was flagged, what evidence was available, and recommended next steps.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              {/* 1. DECISION SUMMARY & HIGHLIGHT BANNER */}
              <div className={`p-5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                detail.policy_lineage.decision === 'DECLINED' || detail.policy_lineage.decision === 'DECLINE'
                  ? 'bg-red-950/30 border-red-500/40 text-red-100'
                  : detail.policy_lineage.decision === 'REVIEW_REQUIRED' || detail.policy_lineage.decision === 'MANUAL_REVIEW' || detail.policy_lineage.decision === 'CHALLENGED'
                  ? 'bg-amber-950/30 border-amber-500/40 text-amber-100'
                  : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-100'
              }`}>
                <div className="flex items-center gap-3.5">
                  <div className={`w-11 h-11 rounded-lg flex items-center justify-center shrink-0 ${
                    detail.policy_lineage.decision === 'DECLINED' || detail.policy_lineage.decision === 'DECLINE'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                      : detail.policy_lineage.decision === 'REVIEW_REQUIRED' || detail.policy_lineage.decision === 'MANUAL_REVIEW'
                      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                      : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  }`}>
                    {detail.policy_lineage.decision === 'DECLINED' ? <XCircle className="w-6 h-6" /> : detail.policy_lineage.decision === 'REVIEW_REQUIRED' ? <AlertTriangle className="w-6 h-6" /> : <CheckCircle2 className="w-6 h-6" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-slate-900/60 border border-slate-700">
                        {detail.source_provenance === 'AUDIT_LEDGER' ? 'LIVE ENGINE AUDIT RECORD' : detail.source_provenance === 'RAZORPAY_TEST_MODE' ? 'RAZORPAY TEST MODE' : 'DEMO FIXTURE'}
                      </span>
                      <span className="text-xs font-mono font-bold text-slate-300">
                        Ref: {detail.event_ref}
                      </span>
                    </div>
                    <h2 className="text-xl font-bold tracking-tight mt-0.5">
                      {detail.policy_lineage.action === 'DECLINE' && 'AUTOMATED DECLINE: High-Risk Interception'}
                      {detail.policy_lineage.action === 'STEP_UP_CHALLENGE' && 'STEP-UP 2FA: Dynamic Challenge Required'}
                      {detail.policy_lineage.action === 'MANUAL_REVIEW' && 'MANUAL REVIEW: Queued for Analyst Inspection'}
                      {detail.policy_lineage.action === 'APPROVE' && 'AUTHORIZED: Low Risk Clearance'}
                      {!['DECLINE', 'STEP_UP_CHALLENGE', 'MANUAL_REVIEW', 'APPROVE'].includes(detail.policy_lineage.action) && detail.policy_lineage.action}
                    </h2>
                  </div>
                </div>

                <div className="text-right font-mono text-xs text-slate-300 shrink-0">
                  <div>Threshold: <span className="font-bold text-white">θ* = {detail.policy_lineage.operating_threshold}</span></div>
                  <div className="text-[11px] text-slate-400">Decision: <span className="font-bold text-white">{detail.policy_lineage.decision}</span></div>
                </div>
              </div>

              {/* 2. WHY THIS DECISION? (Reason Code Narrative + Lineage) */}
              <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-blue-400" />
                    Why This Decision Was Made
                  </span>
                  <div className="flex items-center gap-2">
                    {detail.why_flagged.risk_score !== null && detail.why_flagged.risk_score !== undefined && (
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                        Operating Score: {detail.why_flagged.risk_score.toFixed(4)}
                      </span>
                    )}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-bold">
                      {detail.why_flagged.risk_band}
                    </span>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-mono font-bold px-2 py-1 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                      {detail.why_flagged.primary_reason_code}
                    </span>
                    {detail.why_flagged.all_reason_codes.filter(c => c !== detail.why_flagged.primary_reason_code).map(code => (
                      <span key={code} className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {code}
                      </span>
                    ))}
                  </div>

                  <p className="text-sm text-slate-200 font-mono bg-slate-950 p-3.5 rounded-lg border border-slate-800/80">
                    {detail.why_flagged.narrative}
                  </p>
                </div>

                {/* Model & Policy Lineage Substrip */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono pt-1">
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">EVALUATING MODEL</span>
                    <span className="text-slate-200 font-bold">{detail.model_lineage.model_name}</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">{detail.model_lineage.model_type}</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">GOVERNING POLICY</span>
                    <span className="text-slate-200 font-bold">{detail.policy_lineage.policy_version}</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Threshold θ* = {detail.policy_lineage.operating_threshold}</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">SYSTEM RESILIENCE</span>
                    <span className={`font-bold ${detail.model_lineage.fallback_triggered ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {detail.model_lineage.fallback_triggered ? 'FALLBACK ACTIVE' : 'NOMINAL PIPELINE'}
                    </span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Circuit Breaker OK</span>
                  </div>
                </div>
              </div>

              {/* 3. DETERMINISTIC HUMAN INVESTIGATOR GUIDANCE (SOP) */}
              <div className="p-5 rounded-xl bg-slate-900/90 border border-blue-500/30 flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-400 font-mono flex items-center gap-1.5">
                    <CheckSquare className="w-4 h-4 text-blue-400" />
                    Standard Operating Procedure (SOP) Guidance
                  </span>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                    detail.investigator_guidance.urgency === 'IMMEDIATE_HOLD' || detail.investigator_guidance.urgency === 'CRITICAL_INTERCEPTION'
                      ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                      : detail.investigator_guidance.urgency === 'HIGH_PRIORITY_REVIEW'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  }`}>
                    {detail.investigator_guidance.urgency.replace('_', ' ')}
                  </span>
                </div>

                <div className="flex flex-col gap-2">
                  <div className="text-xs font-mono text-slate-300">
                    <strong>Investigation Objective:</strong> {detail.investigator_guidance.objective}
                  </div>
                  <div className="text-xs font-mono text-slate-300">
                    <strong>Recommended Review Action:</strong>{' '}
                    <span className="font-bold text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      {detail.investigator_guidance.recommended_action}
                    </span>
                  </div>
                </div>

                {/* Protocol Steps Checklist */}
                <div className="flex flex-col gap-1.5 bg-slate-950 p-3.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] font-bold font-mono text-slate-400 uppercase tracking-wider">
                    Recommended Analyst Review Protocol:
                  </span>
                  <ul className="flex flex-col gap-1.5 text-xs font-mono text-slate-200">
                    {detail.investigator_guidance.protocol_steps.map((step, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-400 font-bold shrink-0">•</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Evidence to Inspect */}
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono text-slate-400">
                  <span className="font-semibold text-slate-300">Key Evidence to Inspect:</span>
                  {detail.investigator_guidance.evidence_to_inspect.map((evItem, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {evItem}
                    </span>
                  ))}
                </div>

                <div className="text-[10px] text-slate-500 font-mono border-t border-slate-800/80 pt-2">
                  * Defense-only guidance: Assisting human risk officers with evidence verification. Does not alter engine policy.
                </div>
              </div>

              {/* 4. POINT-IN-TIME AVAILABLE EVIDENCE MATRIX */}
              <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-slate-400" />
                    Point-in-Time Evidence Available at Decision Time
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">Zero Post-Transaction Leakage</span>
                </div>

                {/* 2x3 Feature Matrix */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono text-xs">
                  <div className="p-3 rounded bg-slate-950 border border-slate-800 flex flex-col">
                    <span className="text-[10px] text-slate-500">TRANSACTION AMOUNT</span>
                    <span className="text-sm font-bold text-white mt-1">
                      ${detail.what_happened.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                    <span className="text-[10px] text-slate-400">Channel: {detail.what_happened.channel || detail.what_happened.method}</span>
                  </div>

                  <div className="p-3 rounded bg-slate-950 border border-slate-800 flex flex-col">
                    <span className="text-[10px] text-slate-500">SENDER PRE-TX BALANCE</span>
                    <span className="text-sm font-bold text-slate-200 mt-1">
                      ${(detail.what_happened.sender_old_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                    <span className="text-[10px] text-slate-400">Account: {detail.what_happened.sender_masked}</span>
                  </div>

                  <div className="p-3 rounded bg-slate-950 border border-slate-800 flex flex-col">
                    <span className="text-[10px] text-slate-500">DESTINATION PRE-TX BALANCE</span>
                    <span className="text-sm font-bold text-slate-200 mt-1">
                      ${(detail.what_happened.dest_old_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                    <span className="text-[10px] text-slate-400">Beneficiary: {detail.what_happened.dest_masked}</span>
                  </div>
                </div>

                {/* Anomaly Indicators */}
                {detail.anomaly_indicators.length > 0 && (
                  <div className="flex flex-col gap-2 pt-1">
                    <span className="text-[10px] font-mono uppercase font-bold tracking-wider text-slate-400">
                      Observed Signal Anomalies:
                    </span>
                    <div className="flex flex-col gap-1.5">
                      {detail.anomaly_indicators.map((anom, idx) => (
                        <div key={idx} className="p-2.5 rounded bg-slate-950 border border-slate-800 text-xs font-mono flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                              anom.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'
                            }`}>
                              {anom.severity}
                            </span>
                            <span className="text-slate-200 font-semibold">{anom.signal}</span>
                          </div>
                          <span className="text-slate-400 text-[11px]">{anom.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 5. CRYPTOGRAPHIC AUDIT TRAIL */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 font-mono text-xs flex flex-col gap-2">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-slate-400 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-slate-400" />
                    Cryptographic Audit Ledger Trail
                  </span>
                  <span className="text-emerald-400 text-[10px] bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                    {detail.audit_trail.tamper_evident_status}
                  </span>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-slate-400">
                  <span>Audit Event ID: <code className="text-slate-300">{detail.audit_trail.audit_event_id}</code></span>
                  <span>Chained Hash: <code className="text-slate-300">{(detail.audit_trail.chained_integrity_hash || '').substring(0, 24)}...</code></span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
