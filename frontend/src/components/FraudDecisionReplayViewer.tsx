import React, { useState } from 'react';
import { Play, RotateCcw, ArrowRight, ShieldAlert, ShieldCheck, AlertTriangle, Layers, Info, CheckCircle2 } from 'lucide-react';
import { ReplayRequest, ReplayResponse } from '../types/engine';
import { evaluateReplay } from '../api/client';

export const FraudDecisionReplayViewer: React.FC = () => {
  // Preset Selection
  const [selectedPreset, setSelectedPreset] = useState<'DEMO-03' | 'DEMO-04' | 'DEMO-01'>('DEMO-03');

  // Interactive Replay Inputs
  const [channelType, setChannelType] = useState<string>('TRANSFER');
  const [amount, setAmount] = useState<number>(284100.50);
  const [oldBalance, setOldBalance] = useState<number>(284100.50);
  const [muleFanIn, setMuleFanIn] = useState<number>(1);
  const [alpha, setAlpha] = useState<number>(0.010);

  // Execution State
  const [loading, setLoading] = useState<boolean>(false);
  const [replayResult, setReplayResult] = useState<ReplayResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const applyPreset = (preset: 'DEMO-03' | 'DEMO-04' | 'DEMO-01') => {
    setSelectedPreset(preset);
    setErrorMsg(null);
    if (preset === 'DEMO-03') {
      setChannelType('TRANSFER');
      setAmount(284100.50);
      setOldBalance(284100.50);
      setMuleFanIn(1);
    } else if (preset === 'DEMO-04') {
      setChannelType('TRANSFER');
      setAmount(50.00);
      setOldBalance(1000.00);
      setMuleFanIn(0);
    } else if (preset === 'DEMO-01') {
      setChannelType('PAYMENT');
      setAmount(84.50);
      setOldBalance(5000.00);
      setMuleFanIn(0);
    }
  };

  const handleReplay = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    const req: ReplayRequest = {
      baseline_fixture_id: selectedPreset,
      step: 452,
      type: channelType,
      amount: amount,
      oldbalanceOrg: oldBalance,
      oldbalanceDest: 0.0,
      nameOrig: 'C_REPLAY_SENDER',
      nameDest: 'C_REPLAY_DEST',
      sandbox_context: {
        dest_unique_orig_cnt: muleFanIn > 0 ? muleFanIn : undefined
      },
      alpha: alpha
    };

    try {
      const res = await evaluateReplay(req);
      setReplayResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Replay evaluation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl my-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-purple-400" />
            <h2 className="text-base font-bold text-white tracking-wide">
              Fraud Decision Replay Studio <span className="text-xs font-normal px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">Sandbox Replay</span>
            </h2>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Judge-Facing Decision Sensitivity Console: Modify pre-transaction inputs &amp; behavioral context. Observes Features → Score → Reasons → Policy → Economics.
          </p>
        </div>

        {/* Provenance Badge */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-950 text-slate-300 border border-slate-700 font-mono text-[10px] font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse"></span>
            ZERO PRODUCTION MUTATION
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="mt-3 p-3 text-xs rounded bg-rose-950/60 text-rose-300 border border-rose-800 font-mono">
          {errorMsg}
        </div>
      )}

      {/* Preset Baseline Selection */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 font-mono mr-2">Baseline Scenario:</span>
        <button
          onClick={() => applyPreset('DEMO-03')}
          className={`px-3 py-1.5 rounded text-xs font-mono transition-colors border ${
            selectedPreset === 'DEMO-03'
              ? 'bg-purple-900 text-purple-200 border-purple-600 font-bold'
              : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
          }`}
        >
          DEMO-03: Critical Account Drain
        </button>
        <button
          onClick={() => applyPreset('DEMO-04')}
          className={`px-3 py-1.5 rounded text-xs font-mono transition-colors border ${
            selectedPreset === 'DEMO-04'
              ? 'bg-purple-900 text-purple-200 border-purple-600 font-bold'
              : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
          }`}
        >
          DEMO-04: Benign Cold-Start
        </button>
        <button
          onClick={() => applyPreset('DEMO-01')}
          className={`px-3 py-1.5 rounded text-xs font-mono transition-colors border ${
            selectedPreset === 'DEMO-01'
              ? 'bg-purple-900 text-purple-200 border-purple-600 font-bold'
              : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
          }`}
        >
          DEMO-01: Consumer Payment Bypass
        </button>
      </div>

      {/* Interactive Knobs Form */}
      <form onSubmit={handleReplay} className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-xs">
        <div>
          <label className="text-slate-400 block mb-1 text-[11px]">Channel Route</label>
          <select
            value={channelType}
            onChange={(e) => setChannelType(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
          >
            <option value="TRANSFER">TRANSFER (Scored Channel)</option>
            <option value="CASH_OUT">CASH_OUT (Scored Channel)</option>
            <option value="PAYMENT">PAYMENT (Fast-Path Bypass)</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 block mb-1 text-[11px]">Amount ($)</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
            className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
          />
        </div>

        <div>
          <label className="text-slate-400 block mb-1 text-[11px]">Sender Balance ($)</label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={oldBalance}
            onChange={(e) => setOldBalance(parseFloat(e.target.value) || 0)}
            className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
          />
        </div>

        <div>
          <label className="text-slate-400 block mb-1 text-[11px]">Destination Mule Fan-In</label>
          <select
            value={muleFanIn}
            onChange={(e) => setMuleFanIn(parseInt(e.target.value, 10))}
            className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
          >
            <option value="0">0 (Unseen Account)</option>
            <option value="1">1 Sender (Normal)</option>
            <option value="5">5 Senders (Elevated)</option>
            <option value="15">15 Senders (High Mule Fan-In)</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 block mb-1 text-[11px]">Friction Factor (α: {(alpha * 100).toFixed(1)}%)</label>
          <input
            type="range"
            min="0.001"
            max="0.050"
            step="0.001"
            value={alpha}
            onChange={(e) => setAlpha(parseFloat(e.target.value))}
            className="w-full mt-2 accent-purple-500 cursor-pointer"
          />
        </div>

        <div className="col-span-full pt-2 flex items-center justify-between">
          <div className="text-[11px] text-slate-400">
            Current Drain Ratio: <span className="text-amber-300 font-bold">{(oldBalance > 0 ? (amount / oldBalance * 100).toFixed(1) : '100.0')}%</span>
            {amount === oldBalance && oldBalance > 0 && <span className="ml-2 text-rose-400 font-semibold">(Exact Balance Liquidation Trigger)</span>}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-sans font-medium text-xs transition-colors flex items-center gap-2 shadow-lg disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{loading ? 'Re-Evaluating...' : 'Re-Evaluate in Sandbox'}</span>
          </button>
        </div>
      </form>

      {/* Side-by-Side Comparison Dossier */}
      {replayResult && (
        <div className="mt-5 space-y-4 font-mono">
          {/* Top Level Diff Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Baseline Card */}
            {replayResult.baseline_evaluation ? (
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between pb-2 border-b border-slate-850">
                  <span className="text-xs font-semibold text-slate-400 uppercase">BASELINE DECISION ({replayResult.baseline_fixture_id})</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    replayResult.baseline_evaluation.decision === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                    replayResult.baseline_evaluation.decision === 'DECLINED' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                    'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}>
                    {replayResult.baseline_evaluation.decision}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[10px]">OPERATING SCORE</span>
                    <span className="text-white font-bold text-sm">{replayResult.baseline_evaluation.operating_score.toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">RISK BAND</span>
                    <span className="text-slate-300">{replayResult.baseline_evaluation.risk_band}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-slate-500 block text-[10px]">PRIMARY REASON</span>
                    <span className="text-amber-400 font-semibold">{replayResult.baseline_evaluation.primary_reason_code}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-slate-500 text-xs flex items-center justify-center">
                Select a baseline scenario above for comparative diffing.
              </div>
            )}

            {/* Replay Card */}
            <div className="p-4 rounded-lg bg-slate-950 border border-purple-900/60 shadow-lg">
              <div className="flex items-center justify-between pb-2 border-b border-slate-850">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-purple-300 uppercase">REPLAYED HYPOTHETICAL DECISION</span>
                  {replayResult.deltas?.decision_changed && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-950 text-amber-300 border border-amber-800">TRANSITION</span>
                  )}
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  replayResult.replayed_evaluation.decision === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                  replayResult.replayed_evaluation.decision === 'DECLINED' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                  'bg-amber-950 text-amber-300 border border-amber-800'
                }`}>
                  {replayResult.replayed_evaluation.decision}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px]">OPERATING SCORE</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-white font-bold text-sm">{replayResult.replayed_evaluation.operating_score.toFixed(4)}</span>
                    {replayResult.deltas && (
                      <span className={`text-[10px] font-semibold ${
                        replayResult.deltas.score_delta > 0 ? 'text-rose-400' : 'text-emerald-400'
                      }`}>
                        ({replayResult.deltas.score_delta > 0 ? '+' : ''}{replayResult.deltas.score_delta.toFixed(4)})
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">POLICY ACTION</span>
                  <span className="text-slate-300">{replayResult.replayed_evaluation.action}</span>
                </div>
                <div className="col-span-2">
                  <span className="text-slate-500 block text-[10px]">PRIMARY REASON</span>
                  <span className="text-purple-300 font-semibold">{replayResult.replayed_evaluation.primary_reason_code}</span>
                  <p className="text-[11px] text-slate-400 mt-0.5">{replayResult.replayed_evaluation.narrative}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Economic Scenario Impact */}
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-850">
              <span className="text-xs font-semibold text-slate-300 uppercase">ANALYTICAL ECONOMIC IMPACT</span>
              <span className="text-[10px] text-slate-400 italic">Analytical sensitivity — not Razorpay unit economics</span>
            </div>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <span className="text-slate-500 block text-[10px]">HYPOTHETICAL FRAUD EXPOSURE</span>
                <span className="text-white font-bold text-sm">
                  ${replayResult.economic_impact.hypothetical_fraud_exposure.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Scenario exposure if genuine attack</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ESTIMATED MERCHANT FRICTION COST</span>
                <span className="text-amber-400 font-bold text-sm">
                  ${replayResult.economic_impact.hypothetical_friction_cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">At α = {replayResult.economic_impact.alpha_percentage} friction factor</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ECONOMIC SUMMARY</span>
                <p className="text-[11px] text-slate-300 mt-0.5">{replayResult.economic_impact.economic_narrative}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
