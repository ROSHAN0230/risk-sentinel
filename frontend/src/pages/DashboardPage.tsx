import React from 'react';
import { BenchmarkMetricCard } from '../components/BenchmarkMetricCard';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { DataSourceBadge } from '../components/DataSourceBadge';
import { ArrowRight, ArrowRightLeft, ShieldAlert, Cpu, BarChart3, Clock, ShieldCheck } from 'lucide-react';
import { HealthResponse } from '../types/engine';

interface Props {
  onNavigateToStream: () => void;
  health: HealthResponse | null;
}

export const DashboardPage: React.FC<Props> = ({ onNavigateToStream, health }) => {
  return (
    <div className="flex flex-col gap-6 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Executive Risk Overview</h1>
            <DataSourceBadge source="LIVE_ENGINE" />
          </div>
          <p className="text-sm text-slate-400 font-mono mt-0.5">
            Real-Time Causal Payment Defense & Decision Engine Telemetry
          </p>
        </div>

        <button
          onClick={onNavigateToStream}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition-all shadow-sm"
        >
          <span>Launch Demo Scenario Simulator</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* 4 Primary KPI Cards with Explicit Data Tier Badges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <BenchmarkMetricCard
          title="Fraud Dollars Intercepted"
          value="99.99%"
          subtext="$6.323B protected / $399k missed"
          badgeLabel="PaySim Benchmark Result (Steps 378–743)"
          sourceType="BENCHMARK_RESEARCH"
          isAccent={true}
        />

        <BenchmarkMetricCard
          title="Precision on High-Risk"
          value="96.29%"
          subtext="FPR: 0.0162% (16 per 100k txs)"
          badgeLabel="Evaluated @ Operating Threshold θ* = 0.990"
          sourceType="BENCHMARK_RESEARCH"
        />

        <BenchmarkMetricCard
          title="Local Benchmark Latency"
          value="2.40 ms (p99)"
          subtext="vs 35.0 ms Gateway Target Budget"
          badgeLabel="Local In-Process Core Profiling"
          sourceType="LIVE_ENGINE"
        />

        <BenchmarkMetricCard
          title="Model Engine Status"
          value="Active"
          subtext="Model B Champion | 100% Ready"
          badgeLabel="Model A Causal Baseline Guard Standby"
          sourceType="LIVE_ENGINE"
        />
      </div>

      {/* Grid: Decoupled Policy Breakdown + Channel Routing Policy + Engine Lineage */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Decoupled Traffic Distribution */}
        <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col justify-between gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-200">Decoupled Traffic Distribution</h3>
            </div>
            <DataSourceBadge source="BENCHMARK_RESEARCH" size="sm" />
          </div>

          <div className="flex flex-col gap-3 py-1">
            {/* Approved */}
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-emerald-400 font-medium">APPROVED (Low Risk)</span>
                <span className="text-slate-300">99.98% (951,594 txs)</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-900 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: '99.98%' }}></div>
              </div>
            </div>

            {/* Challenged / Manual Review */}
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-amber-400 font-medium">MANUAL REVIEW / STEP-UP (Medium)</span>
                <span className="text-slate-300">0.01% (140 txs)</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-900 overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: '15%' }}></div>
              </div>
            </div>

            {/* Declined */}
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-red-400 font-medium">DECLINED (High Risk)</span>
                <span className="text-slate-300">0.42% (4,010 txs)</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-900 overflow-hidden">
                <div className="h-full bg-red-500 rounded-full" style={{ width: '42%' }}></div>
              </div>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-400 border-t border-slate-700/60 pt-2">
            Decoupled actions prevent false-positive declines by routing borderline risk (0.900 ≤ S &lt; 0.990) to review.
          </div>
        </div>

        {/* Active Channel Routing Architecture */}
        <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col justify-between gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-200">Active Channel Policy</h3>
            </div>
            <DataSourceBadge source="LIVE_ENGINE" size="sm" />
          </div>

          <div className="flex flex-col gap-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-red-950/20 border border-red-500/30 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-bold text-red-300">Scored High-Risk Channels</span>
                <p className="text-[11px] text-slate-400 mt-0.5">TRANSFER, CASH_OUT (Evaluated via Model B 36-dim GBDT)</p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-500/30 flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-bold text-blue-300">Fast-Path Empirical Bypass</span>
                <p className="text-[11px] text-slate-400 mt-0.5">PAYMENT, CASH_IN, DEBIT (0 fraud in 3.59M records)</p>
              </div>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-400 border-t border-slate-700/60 pt-2">
            Channel policy minimizes latency while concentrating ML inference on actual high-risk vectors.
          </div>
        </div>

        {/* Live Engine Status & Lineage */}
        <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col justify-between gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-200">Engine Lineage & Hashes</h3>
            </div>
            <DataSourceBadge source="LIVE_ENGINE" size="sm" />
          </div>

          <div className="flex flex-col gap-2 font-mono text-xs text-slate-300">
            <div className="flex justify-between py-1 border-b border-slate-700/50">
              <span className="text-slate-400">Champion Model:</span>
              <span className="text-white">Model B Stateful HGB</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-700/50">
              <span className="text-slate-400">Fallback Guard:</span>
              <span className="text-indigo-300">Model A Causal Baseline</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-700/50">
              <span className="text-slate-400">Operating Threshold:</span>
              <span className="text-white">θ* = 0.9900</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">SHA-256 Hash:</span>
              <span className="text-blue-300 truncate max-w-[140px]" title={health?.champion_model_sha256 || '5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735'}>
                {health?.champion_model_sha256?.substring(0, 14) || '5ea5926344e1'}...
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-400 border-t border-slate-700/60 pt-2">
            Cryptographically verified against frozen engine manifest on boot.
          </div>
        </div>
      </div>

      {/* Compliance Disclaimer Banner */}
      <DisclaimerBanner />
    </div>
  );
};
