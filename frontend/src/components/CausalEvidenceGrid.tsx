import React from 'react';
import { DollarSign, Wallet, Percent, ArrowRightLeft, UserCheck, Users } from 'lucide-react';

interface Props {
  evidence: Record<string, any>;
}

export const CausalEvidenceGrid: React.FC<Props> = ({ evidence }) => {
  const amt = evidence.amount || 0;
  const oldOrig = evidence.oldbalanceOrg || 0;
  const drainPct = evidence.liquidation_pct !== undefined 
    ? evidence.liquidation_pct 
    : (oldOrig > 0 ? (amt / oldOrig) * 100 : 0);
  const channel = evidence.channel || 'TRANSFER';
  const isColdStart = evidence.is_sender_cold_start === 1;
  const muleCount = evidence.dest_unique_orig_cnt || 0;

  return (
    <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <h3 className="text-sm font-semibold text-slate-200">Point-in-Time Pre-Transaction Evidence Matrix</h3>
        <span className="text-xs font-mono text-slate-400">Strictly Pre-Transaction State (t &lt; execution)</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {/* 1. Transaction Amount */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <DollarSign className="w-3.5 h-3.5 text-blue-400" />
            <span>Amount Requested</span>
          </div>
          <span className="text-base font-bold font-mono text-white">
            ${Number(amt).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>

        {/* 2. Sender Old Balance */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <Wallet className="w-3.5 h-3.5 text-blue-400" />
            <span>Sender Old Balance</span>
          </div>
          <span className="text-base font-bold font-mono text-white">
            ${Number(oldOrig).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>

        {/* 3. Liquidity Drain % */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <Percent className="w-3.5 h-3.5 text-amber-400" />
            <span>Liquidity Outflow</span>
          </div>
          <span className={`text-base font-bold font-mono ${drainPct >= 99 ? 'text-red-400' : drainPct >= 90 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {Number(drainPct).toFixed(1)}%
          </span>
        </div>

        {/* 4. Channel Route */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <ArrowRightLeft className="w-3.5 h-3.5 text-blue-400" />
            <span>Channel Route</span>
          </div>
          <span className="text-base font-bold font-mono text-blue-300">
            {channel}
          </span>
        </div>

        {/* 5. Sender History Context */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <UserCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>Sender Context</span>
          </div>
          <span className="text-sm font-semibold font-mono text-slate-200">
            {isColdStart ? 'Cold Start (0 prior txs)' : 'Established Account'}
          </span>
        </div>

        {/* 6. Recipient Mule Aggregation */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-700/80 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <Users className="w-3.5 h-3.5 text-amber-400" />
            <span>Recipient Inflow</span>
          </div>
          <span className="text-sm font-semibold font-mono text-slate-200">
            {muleCount > 1 ? `${muleCount} Senders Aggregated` : 'Standard Recipient'}
          </span>
        </div>
      </div>
    </div>
  );
};
