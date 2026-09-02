import React, { useState, useEffect } from 'react';
import { DataSourceBadge } from '../components/DataSourceBadge';
import { getCostSimulation, getBenchmarkSummary } from '../api/client';
import { CostSimulationResponse, CostSimulationPoint, BenchmarkSummaryResponse } from '../types/engine';
import { Sliders, Shield, Database, AlertCircle, BookOpen, CheckCircle2, Info, Lock, ArrowUpRight, TrendingUp, Layers } from 'lucide-react';

export const BenchmarksPage: React.FC = () => {
  // Analytical sensitivity exploration state (Validation Split)
  const [alpha, setAlpha] = useState<number>(0.01); // 1.0% default
  const [selectedThreshold, setSelectedThreshold] = useState<number>(0.990);
  const [simData, setSimData] = useState<CostSimulationResponse | null>(null);
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Fetch canonical held-out benchmark summary on mount
  useEffect(() => {
    getBenchmarkSummary()
      .then((data) => setBenchmarkSummary(data))
      .catch((err) => {
        console.error('Failed to load benchmark summary:', err);
        setLoadError('Failed to load canonical benchmark summary from backend API.');
      });
  }, []);

  // Fetch validation cost simulation whenever alpha changes
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    getCostSimulation(alpha)
      .then((data) => {
        if (isMounted) {
          setSimData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load cost simulation:', err);
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [alpha]);

  // Find currently selected threshold point in validation simulation table
  const selectedPoint: CostSimulationPoint | undefined = simData?.simulation_table.find(
    (p) => Math.abs(p.threshold - selectedThreshold) < 0.0001
  ) || simData?.production_operating_point;

  // Dynamic values derived from canonical benchmark summary
  const cm = benchmarkSummary?.confusion_matrix;
  const testFnDollars = benchmarkSummary?.fraud_dollars_missed ?? 399045.08;
  const testFpVolume = benchmarkSummary?.flagged_nonfraud_volume ?? 9216222.88;
  const testInterventionCost = testFpVolume * alpha;
  const testTotalCost = testFnDollars + testInterventionCost;

  return (
    <div className="flex flex-col gap-6 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Benchmark &amp; Evaluation</h1>
            <DataSourceBadge source="BENCHMARK_RESEARCH" />
          </div>
          <p className="text-sm text-slate-400 font-mono mt-0.5">
            PaySim Synthetic Benchmark — Chronological Future Held-Out Test (Steps 378–743)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Lock className="w-3.5 h-3.5" />
            OPERATING THRESHOLD: θ* = 0.990
          </span>
        </div>
      </div>

      {/* Global Institutional Disclaimer Banner */}
      <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            <strong>Evaluation Scope:</strong> PaySim synthetic benchmark — held-out future test. Not Razorpay production performance.
          </span>
        </div>
        <span className="text-[11px] text-amber-400/80 font-mono hidden md:inline">
          Threshold θ* = 0.990 selected on validation steps 323–377; held-out test evaluated once.
        </span>
      </div>

      {loadError && (
        <div className="p-3 bg-red-950/40 border border-red-500/40 text-red-300 text-xs font-mono rounded-lg">
          {loadError}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 1: CANONICAL FUTURE HELD-OUT TEST BENCHMARK (PRIMARY HIERARCHY) */}
      {/* ========================================================================= */}
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-purple-400" />
              <h2 className="text-lg font-bold text-white tracking-wide">
                Future Held-Out Test Performance
              </h2>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-purple-950 text-purple-300 border border-purple-800">
                Steps 378–743 (955,744 txns)
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Evaluated strictly once at frozen operating threshold θ* = 0.990 (selected on validation steps 323–377).
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400 bg-slate-950 px-3 py-1 rounded border border-slate-800">
            Source: <code className="text-purple-300">GET /v1/analytics/benchmark-summary</code>
          </span>
        </div>

        {/* 4 Hero KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Precision */}
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between gap-2">
            <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">MEASURED PRECISION</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white font-mono">
                {benchmarkSummary ? `${benchmarkSummary.precision_percent.toFixed(2)}%` : '96.29%'}
              </span>
              <span className="text-xs text-emerald-400 font-mono">High Precision</span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 border-t border-slate-850 pt-2">
              154 false alarms in 955,744 transactions
            </p>
          </div>

          {/* Card 2: Recall */}
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between gap-2">
            <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">MEASURED RECALL</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white font-mono">
                {benchmarkSummary ? `${benchmarkSummary.recall_percent.toFixed(2)}%` : '99.65%'}
              </span>
              <span className="text-xs text-emerald-400 font-mono">High Coverage</span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 border-t border-slate-850 pt-2">
              3,996 of 4,010 malicious transfers intercepted
            </p>
          </div>

          {/* Card 3: Intercepted Dollars */}
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between gap-2">
            <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">FRAUD DOLLARS INTERCEPTED</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-emerald-400 font-mono">
                $6.323B
              </span>
              <span className="text-xs text-emerald-400 font-mono">
                {benchmarkSummary ? `${benchmarkSummary.fraud_dollar_interception_percent.toFixed(4)}%` : '99.9937%'}
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 border-t border-slate-850 pt-2">
              ${benchmarkSummary ? benchmarkSummary.fraud_dollars_intercepted.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '6,323,408,725.18'} captured
            </p>
          </div>

          {/* Card 4: Operating Policy */}
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between gap-2">
            <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">FROZEN OPERATING POINT</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-white font-mono">θ* = 0.990</span>
              <span className="text-xs text-blue-400 font-mono">θ_med = 0.900</span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 border-t border-slate-850 pt-2">
              Selected on validation; locked before test
            </p>
          </div>
        </div>

        {/* Standard 4-Cell Confusion Matrix */}
        <div className="mt-2 bg-slate-950 p-5 rounded-lg border border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-850">
            <div>
              <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                Canonical 4-Cell Confusion Matrix (Steps 378–743)
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Evaluated on 955,744 held-out test transactions (4,010 ground-truth frauds, 951,734 clean transactions).
              </p>
            </div>
            <div className="text-xs font-mono text-slate-400 bg-slate-900 px-3 py-1 rounded border border-slate-800">
              Total Matrix Balance: <strong className="text-white">955,744</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Predicted Clean / Approved Partition */}
            <div className="space-y-3">
              <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider block">
                PREDICTED CLEAN (ACTION: APPROVE — SCORE &lt; 0.990)
              </span>

              {/* Cell: True Negative */}
              <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-emerald-400">TRUE NEGATIVES (TN)</span>
                  <span className="text-lg font-mono font-bold text-white">
                    {cm ? cm.tn.toLocaleString() : '951,580'}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-400 mt-1">
                  Legitimate transactions correctly approved with zero operational friction.
                </p>
              </div>

              {/* Cell: False Negative */}
              <div className="p-4 rounded-lg bg-rose-950/20 border border-rose-900/40">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-rose-400">FALSE NEGATIVES (FN)</span>
                  <span className="text-lg font-mono font-bold text-rose-300">
                    {cm ? cm.fn.toLocaleString() : '14'}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-400 mt-1">
                  Malicious transactions unintercepted. Missed fraud dollars: <strong className="text-rose-300">${testFnDollars.toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong> out of $6.32B total.
                </p>
              </div>
            </div>

            {/* Predicted Fraud / Declined Partition */}
            <div className="space-y-3">
              <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider block">
                PREDICTED FRAUD (ACTION: DECLINE — SCORE &ge; 0.990)
              </span>

              {/* Cell: False Positive */}
              <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-900/40">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-amber-400">FALSE POSITIVES (FP)</span>
                  <span className="text-lg font-mono font-bold text-amber-300">
                    {cm ? cm.fp.toLocaleString() : '154'}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-400 mt-1">
                  Clean transactions flagged. Flagged non-fraud volume: <strong className="text-amber-300">${testFpVolume.toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong>.
                </p>
              </div>

              {/* Cell: True Positive */}
              <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-800/60 shadow-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-emerald-400">TRUE POSITIVES (TP)</span>
                  <span className="text-xl font-mono font-bold text-emerald-300">
                    {cm ? cm.tp.toLocaleString() : '3,996'}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-400 mt-1">
                  Malicious transfers intercepted before settlement. Intercepted dollars: <strong className="text-emerald-300">${benchmarkSummary ? benchmarkSummary.fraud_dollars_intercepted.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '6,323,408,725.18'}</strong>.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-850 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
            <span>
              * Scientific Integrity Disclosure: 14 unintercepted frauds prove that Risk Sentinel does not fabricate a "perfect model" narrative.
            </span>
            <span className="text-purple-300 font-semibold">
              Precision: {benchmarkSummary?.precision_percent ?? 96.29}% | Recall: {benchmarkSummary?.recall_percent ?? 99.65}%
            </span>
          </div>
        </div>

        {/* Financial Outcome Breakdown */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-950 p-4 rounded-lg border border-slate-800">
          <div className="font-mono text-xs flex flex-col gap-1">
            <span className="text-slate-400">Intercepted Fraud Volume</span>
            <span className="text-base font-bold text-emerald-400">
              ${benchmarkSummary ? benchmarkSummary.fraud_dollars_intercepted.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '6,323,408,725.18'}
            </span>
            <span className="text-[10px] text-slate-500">99.9937% of malicious dollars protected</span>
          </div>

          <div className="font-mono text-xs flex flex-col gap-1">
            <span className="text-slate-400">Missed Fraud Dollars (FN)</span>
            <span className="text-base font-bold text-rose-400">
              ${testFnDollars.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[10px] text-slate-500">14 unintercepted malicious transfers</span>
          </div>

          <div className="font-mono text-xs flex flex-col gap-1">
            <span className="text-slate-400">Flagged Clean Volume (FP)</span>
            <span className="text-base font-bold text-amber-400">
              ${testFpVolume.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[10px] text-slate-500">154 false alarms across 955,744 transactions</span>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 2: VALIDATION SENSITIVITY & THRESHOLD EXPLORER (STEPS 323–377) */}
      {/* ========================================================================= */}
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase tracking-wide">
                Validation Split
              </span>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Validation Decision Economics &amp; False-Positive Simulator
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Steps 323–377 (973,173 txns, 570 frauds) — Used strictly for selecting θ* = 0.990 before held-out test evaluation.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Lock className="w-3.5 h-3.5" />
              LOCKED THRESHOLD: θ* = 0.990
            </span>
          </div>
        </div>

        {/* Permanent Institutional Disclaimer */}
        <div className="p-3.5 rounded-lg bg-amber-500/5 border border-amber-500/20 text-amber-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Methodological Scope:</strong> Exploratory scenario sensitivity modeling — does not represent Razorpay unit economics.
            </span>
          </div>
          <span className="text-[11px] text-amber-400/80 font-mono">
            Analytical sensitivity exploration only — does not alter frozen production policy.
          </span>
        </div>

        {/* Dual Controls: Alpha Multiplier Slider + Measured Threshold Selector */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-950 p-5 rounded-lg border border-slate-800/80">
          {/* Control 1: Alpha Slider */}
          <div className="flex flex-col gap-3 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-300 font-semibold flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-amber-400" />
                Intervention Friction Factor (α):
              </span>
              <span className="text-amber-400 font-bold text-sm bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/20">
                {(alpha * 100).toFixed(1)}%
              </span>
            </div>

            <input
              type="range"
              min="0.001"
              max="0.050"
              step="0.001"
              value={alpha}
              onChange={(e) => setAlpha(parseFloat(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
            />

            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0.1% (Near-Zero Friction)</span>
              <span>1.0% (Standard Baseline)</span>
              <span>5.0% (Severe Friction)</span>
            </div>
          </div>

          {/* Control 2: Operating Threshold Selection */}
          <div className="flex flex-col gap-3 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-300 font-semibold flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-blue-400" />
                Explored Threshold Operating Point:
              </span>
              <span className="text-blue-400 font-bold text-sm bg-blue-500/10 px-2.5 py-0.5 rounded border border-blue-500/20">
                θ = {selectedThreshold.toFixed(3)}
              </span>
            </div>

            <select
              value={selectedThreshold}
              onChange={(e) => setSelectedThreshold(parseFloat(e.target.value))}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white font-mono text-xs focus:outline-none focus:border-blue-500"
            >
              {simData?.simulation_table.map((row) => (
                <option key={row.threshold} value={row.threshold}>
                  θ = {row.threshold.toFixed(3)} {row.is_production_threshold ? '(Active Production Policy)' : ''}
                </option>
              ))}
            </select>

            <div className="text-[10px] text-slate-500">
              Validation split cost minimum observed at θ = 0.990 across all tested α values.
            </div>
          </div>
        </div>

        {/* 15-Point Validation Sensitivity Table */}
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Threshold</th>
                <th className="py-2.5 px-3">Precision</th>
                <th className="py-2.5 px-3">Recall</th>
                <th className="py-2.5 px-3">FP Count</th>
                <th className="py-2.5 px-3">FN Count</th>
                <th className="py-2.5 px-3">Missed Fraud ($)</th>
                <th className="py-2.5 px-3">Friction Cost (α×FP)</th>
                <th className="py-2.5 px-3">Total Cost</th>
                <th className="py-2.5 px-3 text-right">Policy Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {simData?.simulation_table.map((row) => {
                const isSelected = Math.abs(row.threshold - selectedThreshold) < 0.0001;
                const isProd = row.is_production_threshold;

                return (
                  <tr
                    key={row.threshold}
                    onClick={() => setSelectedThreshold(row.threshold)}
                    className={`cursor-pointer transition-colors ${
                      isProd
                        ? 'bg-blue-950/30 hover:bg-blue-900/40 text-white'
                        : isSelected
                        ? 'bg-slate-800/60 hover:bg-slate-800 text-white'
                        : 'hover:bg-slate-800/30'
                    }`}
                  >
                    <td className="py-2 px-3 font-bold">
                      θ = {row.threshold.toFixed(3)}
                    </td>
                    <td className="py-2 px-3">{(row.precision * 100).toFixed(2)}%</td>
                    <td className="py-2 px-3">{(row.recall * 100).toFixed(2)}%</td>
                    <td className="py-2 px-3">{row.fp}</td>
                    <td className="py-2 px-3 text-red-400">{row.fn}</td>
                    <td className="py-2 px-3">
                      ${row.missed_fraud_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 text-amber-400">
                      ${row.friction_cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 font-bold text-white">
                      ${row.total_cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {isProd ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          Active Policy (θ*=0.990)
                        </span>
                      ) : row.is_validation_cost_minimum ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-300 border border-blue-500/20">
                          Cost Minimum
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500">Exploratory</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 3: DATASET FORENSICS & SCIENTIFIC LIMITATIONS */}
      {/* ========================================================================= */}
      <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col gap-3 font-mono text-xs">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-200">PaySim Dataset Forensic Disclosures &amp; Scientific Limits</h3>
        </div>

        <p className="text-slate-300 leading-relaxed font-sans text-sm">
          PaySim is an academic synthetic benchmark simulating mobile money transactions. Statistical forensics revealed three structural characteristics:
        </p>

        <ul className="list-disc pl-5 space-y-1 text-slate-400">
          <li>
            <strong className="text-slate-300">99.85% Single-Use Senders:</strong> 6,353,307 unique senders across 6,362,620 rows. Senders rarely reappear in the synthetic trace.
          </li>
          <li>
            <strong className="text-slate-300">97.82% Exact Balance Drains:</strong> Synthetic agents executed exact 100% balance liquidations upon account compromise.
          </li>
          <li>
            <strong className="text-slate-300">Channel Exclusivity in Test Horizon:</strong> In the future test split (Steps 378–743), 547,667 transactions (~$40.34B) in CASH_IN, DEBIT, and PAYMENT contained 0 fraud transactions. Fraud occurred strictly in TRANSFER and CASH_OUT channels.
          </li>
          <li>
            <strong className="text-slate-300">Causal Point-in-Time Construction:</strong> Real-time models use only pre-transaction data. Post-transaction balance fields (<code className="text-purple-300">newbalanceOrig</code>, <code className="text-purple-300">newbalanceDest</code>) are purged to prevent outcome leakage.
          </li>
          <li>
            <strong className="text-slate-300">Model Score Semantics:</strong> Model scores represent decision thresholds under validation class-weight balance; they are not calibrated real-world probabilities.
          </li>
          <li>
            <strong className="text-slate-300">Gateway Latency Budget:</strong> The 35ms latency target is an internal engineering budget, not a Razorpay SLA.
          </li>
        </ul>

        <div className="mt-2 p-3 rounded bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-sans">
          <strong>Architectural Context — Not Production Telemetry:</strong> In enterprise payment gateways, customer accounts persist over years. Model B stateful velocity and destination mule tracking provide the essential defensive barrier against multi-day micro-drain attacks that single-transaction models cannot detect.
        </div>
      </div>
    </div>
  );
};
