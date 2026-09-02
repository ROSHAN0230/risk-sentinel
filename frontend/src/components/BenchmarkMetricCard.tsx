import React from 'react';
import { DataSourceBadge } from './DataSourceBadge';

interface Props {
  title: string;
  value: string;
  subtext: string;
  badgeLabel?: string;
  sourceType?: 'LIVE_ENGINE' | 'BENCHMARK_RESEARCH' | 'DEMO_SCENARIO';
  isAccent?: boolean;
}

export const BenchmarkMetricCard: React.FC<Props> = ({
  title,
  value,
  subtext,
  badgeLabel,
  sourceType = 'BENCHMARK_RESEARCH',
  isAccent = false
}) => {
  return (
    <div className={`p-5 rounded-xl border transition-all flex flex-col justify-between gap-3 ${
      isAccent
        ? 'bg-blue-950/20 border-blue-500/40 shadow-sm'
        : 'bg-slate-800/80 border-slate-700 hover:border-slate-600'
    }`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">{title}</span>
        <DataSourceBadge source={sourceType} />
      </div>

      <div>
        <span className="text-3xl font-bold font-mono tracking-tight text-white">{value}</span>
        <p className="text-xs font-mono text-slate-400 mt-1">{subtext}</p>
      </div>

      {badgeLabel && (
        <div className="pt-2 border-t border-slate-700/60">
          <span className="text-[11px] font-mono text-slate-400">{badgeLabel}</span>
        </div>
      )}
    </div>
  );
};
