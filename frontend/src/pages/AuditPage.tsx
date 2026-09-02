import React, { useEffect, useState } from 'react';
import { AuditEvent } from '../types/engine';
import { getAuditEvents } from '../api/client';
import { AuditTimeline } from '../components/AuditTimeline';
import { DataSourceBadge } from '../components/DataSourceBadge';
import { ShieldCheck, RefreshCw, Lock, AlertCircle } from 'lucide-react';

export const AuditPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchEvents = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await getAuditEvents(50);
      setEvents(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch audit ledger events');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  return (
    <div className="flex flex-col gap-6 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Tamper-Evident Audit Ledger</h1>
            <DataSourceBadge source="LIVE_ENGINE" />
          </div>
          <p className="text-sm text-slate-400 font-mono mt-0.5">
            Cryptographically Chained Decision Log with PII Masking
          </p>
        </div>

        <button
          onClick={fetchEvents}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-mono text-xs transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Compliance & Chaining Header Card */}
      <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 flex-shrink-0">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-white text-sm">Cryptographic Verification Architecture</span>
            <p className="text-slate-400 text-[11px] mt-0.5">
              Each block embeds the SHA-256 hash of the preceding event, ensuring tamper-evident detection for compliance audits.
            </p>
          </div>
        </div>

        <div className="text-slate-300 bg-slate-900 px-3 py-2 rounded-lg border border-slate-700 flex-shrink-0">
          <span className="text-slate-500">Recorded Blocks:</span>{' '}
          <span className="font-bold text-white">{events.length}</span>
        </div>
      </div>

      {/* Audit Timeline */}
      <AuditTimeline events={events} isLoading={isLoading} />
    </div>
  );
};
