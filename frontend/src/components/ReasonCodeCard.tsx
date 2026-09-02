import React from 'react';
import { ReasonDetails, DecisionEnum, RiskBand } from '../types/engine';
import { ShieldAlert, ShieldCheck, AlertCircle, Info, Cpu, CheckCircle2 } from 'lucide-react';

interface Props {
  reasons: ReasonDetails;
  fallbackActive?: boolean;
  score?: number;
  decision?: DecisionEnum;
  band?: RiskBand;
}

export const ReasonCodeCard: React.FC<Props> = ({
  reasons,
  fallbackActive,
  score,
  decision,
  band,
}) => {
  const isCritical = reasons.primary_code === 'RC_EXACT_BALANCE_DRAIN';
  const isSevere = reasons.primary_code === 'RC_SEVERE_LIQUIDITY_DRAIN' || reasons.primary_code === 'RC_DEST_MULE_VELOCITY';
  const isBenign = reasons.primary_code === 'RC_BENIGN_BASELINE';

  const isApprovedWithElevatedSignal = decision === 'APPROVED' && !isBenign;
  const isDeclined = decision === 'DECLINED';
  const isChallengedOrReview = decision === 'CHALLENGED' || decision === 'REVIEW_REQUIRED';

  let icon = <Info className="w-5 h-5 text-blue-400" />;
  let badgeColor = 'bg-blue-500/10 text-blue-400 border-blue-500/30';
  let cardBorder = 'border-slate-700';

  if (isCritical) {
    icon = <ShieldAlert className="w-5 h-5 text-red-400" />;
    badgeColor = 'bg-red-500/20 text-red-400 border-red-500/40';
    cardBorder = 'border-red-500/30';
  } else if (isSevere) {
    icon = <AlertCircle className="w-5 h-5 text-amber-400" />;
    badgeColor = 'bg-amber-500/20 text-amber-400 border-amber-500/40';
    cardBorder = 'border-amber-500/30';
  } else if (isBenign) {
    icon = <ShieldCheck className="w-5 h-5 text-emerald-400" />;
    badgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  }

  return (
    <div className={`p-5 rounded-xl bg-slate-800/90 border ${cardBorder} flex flex-col gap-3.5`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-semibold text-slate-200">Causal Decision Attribution</span>
        </div>
        <span className={`text-xs font-mono font-medium px-2.5 py-0.5 rounded-full border ${badgeColor}`}>
          {reasons.primary_code}
        </span>
      </div>

      {/* Primary Feature-Level Signal Narrative */}
      <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 text-sm text-slate-200 leading-relaxed font-sans">
        <div className="text-[10px] uppercase font-mono tracking-wider text-slate-400 mb-1 font-semibold">
          Primary Feature Signal:
        </div>
        {reasons.narrative}
      </div>

      {/* Explicit Distinction between Feature-Level Signal and Policy Resolution */}
      {isApprovedWithElevatedSignal && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-xs font-mono text-emerald-300 flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-bold text-emerald-200">Policy Resolution Context:</span>
            <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
              Feature-level indicator ({reasons.primary_code}) was extracted, but the aggregate Operating Risk Score ({score !== undefined ? score.toFixed(4) : 'Low'}) remains below the intervention threshold (θ* = 0.990). Authorized under standard policy without customer friction.
            </p>
          </div>
        </div>
      )}

      {isDeclined && (
        <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/40 text-xs font-mono text-red-300 flex items-start gap-2.5">
          <ShieldAlert className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-bold text-red-200">Automated Intervention:</span>
            <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
              Operating Risk Score ({score !== undefined ? score.toFixed(4) : '0.990+'}) satisfies high-risk threshold (θ* = 0.990). Immediate decline enforced.
            </p>
          </div>
        </div>
      )}

      {isChallengedOrReview && (
        <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 text-xs font-mono text-amber-300 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-bold text-amber-200">Decoupled Policy Routing:</span>
            <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
              Operating Risk Score ({score !== undefined ? score.toFixed(4) : '0.900+'}) is in medium-risk band [0.900, 0.990). Routed to {decision === 'CHALLENGED' ? 'dynamic step-up 2FA challenge' : 'manual review queue'} instead of hard decline.
            </p>
          </div>
        </div>
      )}

      {/* Factor Codes */}
      {reasons.all_codes && reasons.all_codes.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-xs font-mono text-slate-400">Attribution Factors:</span>
          {reasons.all_codes.map((code) => (
            <span key={code} className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-700/80 text-slate-300 border border-slate-600">
              {code}
            </span>
          ))}
        </div>
      )}

      {/* Active Fallback Indicator */}
      {fallbackActive && (
        <div className="mt-1 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/40 text-xs font-mono text-indigo-300 flex items-center gap-2.5">
          <Cpu className="w-4 h-4 text-indigo-400 flex-shrink-0" />
          <span>Evaluated via Model A Causal Baseline Fallback (State Store Bypassed).</span>
        </div>
      )}
    </div>
  );
};
