import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, RefreshCw, Filter, Layers, Database, ArrowUpRight, Search } from 'lucide-react';
import { TransactionRecord, TransactionSummary } from '../types/engine';
import { getTransactions, getTransactionSummary } from '../api/client';
import { DecisionBadge } from './DecisionBadge';
import { RiskBandBadge } from './RiskBandBadge';

interface Props {
  onSelectTransaction?: (tx: TransactionRecord) => void;
  refreshTrigger?: number;
}

export const TransactionMonitoringFeed: React.FC<Props> = ({ onSelectTransaction, refreshTrigger }) => {
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [summary, setSummary] = useState<TransactionSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedProvenance, setSelectedProvenance] = useState<string>('ALL');
  const [selectedDecision, setSelectedDecision] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeTx, setActiveTx] = useState<TransactionRecord | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [txList, sumData] = await Promise.all([
        getTransactions({
          limit: 50,
          provenance: selectedProvenance === 'ALL' ? undefined : selectedProvenance,
          decision: selectedDecision === 'ALL' ? undefined : selectedDecision
        }),
        getTransactionSummary()
      ]);
      setTransactions(txList);
      setSummary(sumData);
      if (txList.length > 0 && !activeTx) {
        setActiveTx(txList[0]);
      }
    } catch (err) {
      console.error('Failed to load transaction monitoring feed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedProvenance, selectedDecision, refreshTrigger]);

  const getProvenanceBadge = (prov: string) => {
    switch (prov) {
      case 'GENUINE_RAZORPAY_TEST_MODE':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-blue-900/60 text-blue-300 border border-blue-500/40">
            RAZORPAY_TEST_MODE
          </span>
        );
      case 'SIMULATED_CONTRACT_TEST':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-900/60 text-amber-300 border border-amber-500/40">
            SIMULATED_CONTRACT
          </span>
        );
      case 'DEMO_FIXTURE':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-purple-900/60 text-purple-300 border border-purple-500/40">
            DEMO_FIXTURE
          </span>
        );
      case 'API_DIRECT':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-900/60 text-emerald-300 border border-emerald-500/40">
            API_DIRECT
          </span>
        );
    }
  };

  const getAutoResponseBadge = (action: string, status: string) => {
    if (action === 'CAPTURE_PERMITTED') {
      return (
        <div className="flex flex-col">
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5" /> CAPTURE_PERMITTED
          </span>
          <span className="text-[10px] text-slate-400 font-mono">{status}</span>
        </div>
      );
    }
    if (action === 'CAPTURE_SUPPRESSED') {
      return (
        <div className="flex flex-col">
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400">
            <ShieldAlert className="w-3.5 h-3.5" /> CAPTURE_SUPPRESSED
          </span>
          <span className="text-[10px] text-amber-300/80 font-mono">{status}</span>
        </div>
      );
    }
    return (
      <div className="flex flex-col">
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
          {action}
        </span>
        <span className="text-[10px] text-slate-500 font-mono">{status}</span>
      </div>
    );
  };

  const filteredTransactions = transactions.filter((tx) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      tx.transaction_id.toLowerCase().includes(q) ||
      (tx.payment_id && tx.payment_id.toLowerCase().includes(q)) ||
      (tx.order_id && tx.order_id.toLowerCase().includes(q)) ||
      (tx.primary_reason_code && tx.primary_reason_code.toLowerCase().includes(q))
    );
  });

  return (
    <div className="p-6 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col gap-6 shadow-lg">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/80 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Database className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">
              Real-Time Transaction Stream &amp; Auto-Response Feed
            </h2>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-blue-900/50 text-blue-300 border border-blue-600/40">
              PERSISTENT STORE
            </span>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-900/50 text-emerald-300 border border-emerald-600/40">
              TEST MODE ONLY
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Pipeline: Transaction Event &rarr; Persistent Store &rarr; Risk Sentinel Evaluation &rarr; Merchant Policy &rarr; Defensive Auto-Response (Capture Permitted vs. Suppressed)
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="self-start md:self-auto px-3 py-1.5 rounded-lg bg-slate-700/80 hover:bg-slate-600 text-slate-200 text-xs font-mono flex items-center gap-2 transition-colors border border-slate-600"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Feed</span>
        </button>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
          <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-700">
            <div className="text-[11px] text-slate-400">TOTAL MONITORED</div>
            <div className="text-xl font-bold text-white mt-1">{summary.total_transactions}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">INR {summary.total_volume_inr.toLocaleString()}</div>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-900/80 border border-emerald-900/40">
            <div className="text-[11px] text-emerald-400 font-semibold">CAPTURE PERMITTED</div>
            <div className="text-xl font-bold text-emerald-300 mt-1">
              {summary.by_auto_response['CAPTURE_PERMITTED'] || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Approved &amp; Authorized</div>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-900/80 border border-rose-900/40">
            <div className="text-[11px] text-rose-400 font-semibold">CAPTURE SUPPRESSED</div>
            <div className="text-xl font-bold text-rose-300 mt-1">
              {summary.by_auto_response['CAPTURE_SUPPRESSED'] || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Zero API capture calls</div>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-900/80 border border-blue-900/40">
            <div className="text-[11px] text-blue-400 font-semibold">RAZORPAY TEST MODE</div>
            <div className="text-xl font-bold text-blue-300 mt-1">
              {(summary.by_provenance['GENUINE_RAZORPAY_TEST_MODE'] || 0) + (summary.by_provenance['SIMULATED_CONTRACT_TEST'] || 0)}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Test Mode Events</div>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 font-mono text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-400 flex items-center gap-1 mr-1">
            <Filter className="w-3.5 h-3.5" /> Provenance:
          </span>
          {['ALL', 'GENUINE_RAZORPAY_TEST_MODE', 'SIMULATED_CONTRACT_TEST', 'DEMO_FIXTURE', 'API_DIRECT'].map((prov) => (
            <button
              key={prov}
              onClick={() => setSelectedProvenance(prov)}
              className={`px-2.5 py-1 rounded text-[11px] transition-colors border ${
                selectedProvenance === prov
                  ? 'bg-blue-600 text-white border-blue-500 font-semibold'
                  : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
            >
              {prov === 'ALL' ? 'ALL SOURCES' : prov.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search tx ID, payment ID, reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-xs"
          />
        </div>
      </div>

      {/* Table of Transactions */}
      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full text-left font-mono text-xs">
          <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider border-b border-slate-700">
            <tr>
              <th className="py-3 px-3">Transaction / Ref</th>
              <th className="py-3 px-3">Provenance</th>
              <th className="py-3 px-3">Amount</th>
              <th className="py-3 px-3">Risk Score</th>
              <th className="py-3 px-3">Policy Decision</th>
              <th className="py-3 px-3">Defensive Auto-Response</th>
              <th className="py-3 px-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/60 bg-slate-900/40">
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400 font-mono">
                  No transaction records found matching active filters.
                </td>
              </tr>
            ) : (
              filteredTransactions.map((tx) => (
                <tr
                  key={tx.transaction_id}
                  onClick={() => {
                    setActiveTx(tx);
                    if (onSelectTransaction) onSelectTransaction(tx);
                  }}
                  className={`hover:bg-slate-800/80 cursor-pointer transition-colors ${
                    activeTx?.transaction_id === tx.transaction_id ? 'bg-slate-800/90' : ''
                  }`}
                >
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-200">{tx.transaction_id}</div>
                    {tx.payment_id && (
                      <div className="text-[10px] text-blue-400">{tx.payment_id}</div>
                    )}
                    <div className="text-[10px] text-slate-400">{new Date(tx.timestamp_iso).toLocaleTimeString()}</div>
                  </td>
                  <td className="py-3 px-3">
                    {getProvenanceBadge(tx.provenance)}
                  </td>
                  <td className="py-3 px-3 font-semibold text-white">
                    {tx.currency} {tx.amount_inr.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="py-3 px-3">
                    {tx.risk_score !== undefined && tx.risk_score !== null ? (
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-white">{tx.risk_score.toFixed(4)}</span>
                        {tx.risk_band && <RiskBandBadge band={tx.risk_band as any} />}
                      </div>
                    ) : (
                      <span className="text-slate-400">N/A</span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    {tx.decision ? (
                      <div className="flex flex-col gap-0.5">
                        <DecisionBadge decision={tx.decision as any} size="sm" />
                        {tx.primary_reason_code && (
                          <span className="text-[10px] text-slate-400 truncate max-w-[130px]">
                            {tx.primary_reason_code}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-400">NOT_EVALUATED</span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    {getAutoResponseBadge(tx.auto_response_action, tx.auto_response_status)}
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveTx(tx);
                      }}
                      className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 font-sans text-xs"
                    >
                      <span>View</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Selected Transaction Inspector Box */}
      {activeTx && (
        <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-700/80 font-mono text-xs flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" />
              <span className="font-bold text-slate-200">Record Inspection: {activeTx.transaction_id}</span>
            </div>
            {getProvenanceBadge(activeTx.provenance)}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-[10px] text-slate-400 uppercase">Routing &amp; Account Details</div>
              <div className="text-slate-300 mt-1">Channel: <span className="text-white">{activeTx.channel_type}</span></div>
              <div className="text-slate-300">Sender: <span className="text-white">{activeTx.sender_masked}</span></div>
              <div className="text-slate-300">Destination: <span className="text-white">{activeTx.dest_masked}</span></div>
              <div className="text-slate-300">Merchant: <span className="text-white">{activeTx.merchant_id}</span></div>
            </div>

            <div>
              <div className="text-[10px] text-slate-400 uppercase">Risk Sentinel Decision</div>
              <div className="text-slate-300 mt-1">Score: <span className="font-bold text-white">{activeTx.risk_score !== undefined && activeTx.risk_score !== null ? activeTx.risk_score.toFixed(4) : 'N/A'}</span></div>
              <div className="text-slate-300">Policy: <span className="text-white">{activeTx.policy_action || 'N/A'}</span></div>
              <div className="text-slate-300">Reason: <span className="text-amber-300">{activeTx.primary_reason_code || 'N/A'}</span></div>
              <div className="text-slate-300">Narrative: <span className="text-slate-400 text-[11px]">{activeTx.reasons_narrative || 'N/A'}</span></div>
            </div>

            <div>
              <div className="text-[10px] text-slate-400 uppercase">Defensive Auto-Response</div>
              <div className="text-slate-300 mt-1">Action: <span className="font-semibold text-white">{activeTx.auto_response_action}</span></div>
              <div className="text-slate-300">Status: <span className="text-white">{activeTx.auto_response_status}</span></div>
              <div className="text-slate-300 truncate">Audit ID: <span className="text-blue-400">{activeTx.audit_event_id || 'N/A'}</span></div>
              <div className="text-slate-300 truncate">Hash: <span className="text-slate-400 text-[10px]">{activeTx.integrity_hash.substring(0, 16)}...</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
