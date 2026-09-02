import React, { useState } from 'react';
import { AuditEvent } from '../types/engine';
import { ShieldCheck, ChevronDown, ChevronUp, Clock, Hash, Lock, CheckCircle2 } from 'lucide-react';
import { DecisionBadge } from './DecisionBadge';
import { DataSourceBadge } from './DataSourceBadge';

interface Props {
  events: AuditEvent[];
  isLoading: boolean;
}

export const AuditTimeline: React.FC<Props> = ({ events, isLoading }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-400 font-mono text-sm bg-slate-800/50 rounded-xl border border-slate-700">
        Loading tamper-evident audit blocks...
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 font-mono text-sm bg-slate-800/50 rounded-xl border border-slate-700">
        No audit events recorded yet. Evaluate a transaction to emit a cryptographically chained block.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {events.map((ev, index) => {
        const isExpanded = expandedId === ev.event_id;
        const maskedSender = ev.input_snapshot_masked?.sender_masked || 'N/A';
        const maskedDest = ev.input_snapshot_masked?.dest_masked || 'N/A';
        const amt = ev.input_snapshot_masked?.amount || 0;
        const score = ev.evaluation_result?.raw_model_score || 0;
        const decision = (ev.evaluation_result?.decision || 'APPROVED') as any;

        return (
          <div
            key={ev.event_id}
            className="rounded-xl bg-slate-800/90 border border-slate-700 overflow-hidden transition-all hover:border-slate-600"
          >
            {/* Summary Bar */}
            <div
              onClick={() => toggleExpand(ev.event_id)}
              className="p-4 cursor-pointer flex flex-wrap items-center justify-between gap-3 hover:bg-slate-700/30"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-mono text-xs font-bold">
                  #{events.length - index}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-200">{ev.event_id}</span>
                    <DecisionBadge decision={decision} size="sm" />
                    <DataSourceBadge source="LIVE_ENGINE" size="sm" />
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mt-0.5">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span>{new Date(ev.event_timestamp_utc).toLocaleTimeString()}</span>
                    <span>•</span>
                    <span>{ev.input_snapshot_masked?.type}</span>
                    <span>•</span>
                    <span className="text-slate-200 font-semibold">${amt.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right hidden sm:block">
                  <div className="text-xs font-mono text-slate-300">
                    <span className="text-slate-500">Route:</span> {maskedSender} → {maskedDest}
                  </div>
                  <div className="text-[11px] font-mono text-slate-400">
                    <span className="text-slate-500">Score:</span> {score.toFixed(4)}
                  </div>
                </div>

                <div className="text-slate-400">
                  {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </div>
              </div>
            </div>

            {/* Expanded Detailed Audit Payload */}
            {isExpanded && (
              <div className="p-4 bg-slate-900 border-t border-slate-700 font-mono text-xs text-slate-300 flex flex-col gap-3">
                {/* Cryptographic Hash Chaining Box */}
                <div className="p-3 rounded-lg bg-blue-950/40 border border-blue-500/30 flex items-start gap-2.5">
                  <Lock className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                  <div className="overflow-hidden">
                    <div className="text-[11px] text-blue-300 font-bold uppercase tracking-wider mb-0.5">
                      Tamper-Evident SHA-256 Integrity Block Hash
                    </div>
                    <div className="text-xs text-blue-200 truncate select-all">{ev.integrity_hash}</div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Computed as <code className="text-blue-300">sha256(prev_block_hash + event_json)</code> to detect any post-decision modification.
                    </div>
                  </div>
                </div>

                {/* Lineage Metadata Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                  <div className="p-2 rounded bg-slate-800 border border-slate-700">
                    <span className="text-slate-400 block">Model Artifact Hash</span>
                    <span className="text-slate-200 truncate block">{ev.lineage?.model_artifact_hash?.substring(0, 16)}...</span>
                  </div>
                  <div className="p-2 rounded bg-slate-800 border border-slate-700">
                    <span className="text-slate-400 block">Active Model</span>
                    <span className="text-slate-200 block">{ev.lineage?.model_type}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-800 border border-slate-700">
                    <span className="text-slate-400 block">Execution Latency</span>
                    <span className="text-slate-200 block">{ev.runtime_telemetry?.execution_latency_ms} ms</span>
                  </div>
                  <div className="p-2 rounded bg-slate-800 border border-slate-700">
                    <span className="text-slate-400 block">Operating Threshold</span>
                    <span className="text-slate-200 block">θ* = {ev.lineage?.operating_threshold}</span>
                  </div>
                </div>

                {/* Raw Event Snapshot JSON */}
                <div className="mt-1">
                  <div className="text-[11px] text-slate-400 mb-1">Masked Payload & Causal Features Snapshot:</div>
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(ev, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
