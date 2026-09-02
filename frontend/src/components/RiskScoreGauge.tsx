import React from 'react';
import { HelpCircle } from 'lucide-react';

interface Props {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskScoreGauge: React.FC<Props> = ({ score }) => {
  const percentage = Math.min(100, Math.max(0, score * 100));

  let colorClass = 'text-emerald-400 bg-emerald-500';
  let bandText = 'LOW RISK';
  let bandBorder = 'border-emerald-500/30';
  
  if (score >= 0.990) {
    colorClass = 'text-red-400 bg-red-500';
    bandText = 'HIGH RISK';
    bandBorder = 'border-red-500/40';
  } else if (score >= 0.900) {
    colorClass = 'text-amber-400 bg-amber-500';
    bandText = 'MEDIUM RISK';
    bandBorder = 'border-amber-500/30';
  }

  return (
    <div className={`p-5 rounded-xl bg-slate-800/90 border ${bandBorder} flex flex-col gap-3.5`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5" title="Operating decision score derived from balanced loss minimization (+7.106 log-odds shift). Not an uncalibrated probability statement.">
          <span className="text-xs font-mono text-slate-300 uppercase tracking-wider font-semibold">Operating Risk Score</span>
          <HelpCircle className="w-3.5 h-3.5 text-slate-400 cursor-help" />
        </div>
        <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-slate-900 border ${bandBorder} ${colorClass.split(' ')[0]}`}>
          {bandText}
        </span>
      </div>

      {/* Numeric Score */}
      <div className="flex items-baseline justify-between">
        <span className="text-4xl font-bold font-mono tracking-tight text-white">
          {score.toFixed(4)}
        </span>
        <span className="text-xs font-mono text-slate-400">Scale: 0.0000 – 1.0000</span>
      </div>

      {/* Progress Track with Threshold Markers */}
      <div className="relative pt-1">
        <div className="w-full h-3 rounded-full bg-slate-900 border border-slate-700 overflow-hidden relative">
          <div
            className={`h-full rounded-full transition-all duration-500 ${colorClass.split(' ')[1]}`}
            style={{ width: `${percentage}%` }}
          ></div>
        </div>

        {/* Threshold Markers */}
        <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1.5">
          <span>0.00 (Low)</span>
          <span className="text-amber-400 font-medium">θ_med = 0.900</span>
          <span className="text-red-400 font-medium">θ_high = 0.990</span>
          <span>1.00</span>
        </div>
      </div>

      {/* Analytical Subtext Note */}
      <div className="text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-700/60 leading-normal">
        Operating score applied against frozen decision thresholds (θ_med = 0.900, θ_high = 0.990).
      </div>
    </div>
  );
};
