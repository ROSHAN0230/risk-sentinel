import React, { useState } from 'react';
import { EvaluateRequest, EvaluateResponse, DemoFixture } from '../types/engine';
import { DemoScenarioSelector } from '../components/DemoScenarioSelector';
import { DecisionBadge } from '../components/DecisionBadge';
import { RiskBandBadge } from '../components/RiskBandBadge';
import { DataSourceBadge } from '../components/DataSourceBadge';
import { evaluateTransaction } from '../api/client';
import { RazorpayWebhookViewer } from '../components/RazorpayWebhookViewer';
import { RazorpayCaptureGateViewer } from '../components/RazorpayCaptureGateViewer';
import { RazorpayLiveCheckoutViewer } from '../components/RazorpayLiveCheckoutViewer';
import { FraudDecisionReplayViewer } from '../components/FraudDecisionReplayViewer';
import { TransactionMonitoringFeed } from '../components/TransactionMonitoringFeed';
import { Activity, Play, ArrowRight, Clock, AlertCircle } from 'lucide-react';

interface Props {
  onInspectTransaction: (response: EvaluateResponse) => void;
  recentEvaluations: EvaluateResponse[];
  setRecentEvaluations: React.Dispatch<React.SetStateAction<EvaluateResponse[]>>;
}

export const StreamPage: React.FC<Props> = ({
  onInspectTransaction,
  recentEvaluations,
  setRecentEvaluations,
}) => {
  const [selectedDemoId, setSelectedDemoId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [feedRefreshTrigger, setFeedRefreshTrigger] = useState<number>(0);

  // Custom Transaction State
  const [customType, setCustomType] = useState<'TRANSFER' | 'CASH_OUT' | 'PAYMENT'>('TRANSFER');
  const [customAmount, setCustomAmount] = useState<number>(100000);
  const [customBalance, setCustomBalance] = useState<number>(100000);
  const [customSender, setCustomSender] = useState<string>('C_CUSTOM_ORIG');
  const [customDest, setCustomDest] = useState<string>('C_CUSTOM_DEST');

  const handleSelectDemo = async (fixture: DemoFixture) => {
    setSelectedDemoId(fixture.id);
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const resp = await evaluateTransaction(fixture.request);
      setRecentEvaluations((prev) => [resp, ...prev.slice(0, 19)]);
      setFeedRefreshTrigger((prev) => prev + 1);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error communicating with decision engine backend.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunCustom = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    const req: EvaluateRequest = {
      transaction_id: `tx-custom-${Date.now().toString().slice(-6)}`,
      step: 450,
      type: customType,
      amount: customAmount,
      nameOrig: customSender,
      oldbalanceOrg: customBalance,
      nameDest: customDest,
      oldbalanceDest: 0.0,
    };

    try {
      const resp = await evaluateTransaction(req);
      setRecentEvaluations((prev) => [resp, ...prev.slice(0, 19)]);
      setFeedRefreshTrigger((prev) => prev + 1);
    } catch (err: any) {
      setErrorMsg(err.message || 'Validation or evaluation error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-bold text-white tracking-tight">Transaction Stream & Evaluation Simulator</h1>
          <DataSourceBadge source="LIVE_ENGINE" />
        </div>
        <p className="text-sm text-slate-400 font-mono mt-0.5">
          Interactive On-Demand Evaluation Console (Razorpay Test Mode, Demo Presets &amp; Custom Live Injection)
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-white font-bold">✕</button>
        </div>
      )}

      {/* Primary Hero: Live Razorpay Test Mode Gateway & Pre-Capture Gate */}
      <RazorpayLiveCheckoutViewer />


      {/* Demo Scenario Launcher */}
      <DemoScenarioSelector
        selectedDemoId={selectedDemoId}
        onSelectDemo={handleSelectDemo}
        isLoading={isLoading}
      />

      {/* Split Grid: Custom Transaction Form + Live Stream Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Custom Transaction Injector Form */}
        <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-200">Custom Transaction Injector</h3>
              <DataSourceBadge source="LIVE_ENGINE" size="sm" />
            </div>

            <form onSubmit={handleRunCustom} className="flex flex-col gap-3 font-mono text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Channel Route:</label>
                <select
                  value={customType}
                  onChange={(e) => setCustomType(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="TRANSFER">TRANSFER (Scored Channel)</option>
                  <option value="CASH_OUT">CASH_OUT (Scored Channel)</option>
                  <option value="PAYMENT">PAYMENT (Fast-Path Bypass)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Amount ($):</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={customAmount}
                  onChange={(e) => setCustomAmount(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Sender Old Balance ($):</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={customBalance}
                  onChange={(e) => setCustomBalance(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="text-[11px] text-slate-400 pt-1">
                Tip: Setting <span className="text-amber-300 font-semibold">Old Balance == Amount</span> triggers exact balance liquidation defense.
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="mt-2 w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-sans font-medium transition-all shadow-sm flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4" />
                <span>Evaluate Transaction</span>
              </button>
            </form>
          </div>
        </div>

        {/* Live Evaluated Transactions Table */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col gap-4 overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400 animate-pulse" />
              <h3 className="text-sm font-semibold text-slate-200">Recent Engine Evaluations ({recentEvaluations.length})</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">Click row to inspect decision</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider border-b border-slate-700">
                <tr>
                  <th className="py-2.5 px-3">Tx ID</th>
                  <th className="py-2.5 px-3">Operating Score</th>
                  <th className="py-2.5 px-3">Band</th>
                  <th className="py-2.5 px-3">Decision</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60">
                {recentEvaluations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-400 font-mono">
                      No live evaluations yet. Click any demo preset above or submit a custom transaction.
                    </td>
                  </tr>
                ) : (
                  recentEvaluations.map((item) => (
                    <tr
                      key={item.evaluation_id}
                      onClick={() => onInspectTransaction(item)}
                      className="hover:bg-slate-700/40 cursor-pointer transition-colors"
                    >
                      <td className="py-2.5 px-3 font-semibold text-slate-200 truncate max-w-[120px]">
                        {item.transaction_id}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-white">
                        {item.risk_score.toFixed(4)}
                      </td>
                      <td className="py-2.5 px-3">
                        <RiskBandBadge band={item.risk_band} />
                      </td>
                      <td className="py-2.5 px-3">
                        <DecisionBadge decision={item.decision} size="sm" />
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {item.engine_metadata?.execution_latency_ms?.toFixed(1) || '1.8'} ms
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 font-sans text-xs">
                          Inspect <ArrowRight className="w-3 h-3" />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Real-Time Transaction Monitoring & Auto-Response Feed (Persistent Store) */}
      <TransactionMonitoringFeed refreshTrigger={feedRefreshTrigger} />

      {/* Phase 2: Judge-Facing Fraud Decision Replay Studio */}
      <FraudDecisionReplayViewer />

      {/* Razorpay Test Mode Capture Gate */}
      <RazorpayCaptureGateViewer />

      {/* Razorpay Test Mode Webhook Monitor */}
      <RazorpayWebhookViewer />
    </div>
  );
};
