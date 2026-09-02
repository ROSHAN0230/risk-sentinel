import React, { useState, useEffect } from 'react';
import { getWebhookEvents, postRazorpayWebhook } from '../api/client';
import { NormalizedWebhookEvent } from '../types/engine';
import { ShieldAlert, CheckCircle2, AlertTriangle, ArrowDownRight, RefreshCw, Send, Lock } from 'lucide-react';

export const RazorpayWebhookViewer: React.FC = () => {
  const [events, setEvents] = useState<NormalizedWebhookEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'feed' | 'simulate'>('feed');

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const data = await getWebhookEvents(20);
      setEvents(data);
    } catch (err) {
      console.error('Failed to load webhook events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleSimulateRawWebhook = async () => {
    setSimulating(true);
    try {
      const sampleRaw = {
        entity: "event",
        account_id: "acc_rzp_test_merchant",
        event: "payment.authorized",
        contains: ["payment"],
        payload: {
          payment: {
            entity: {
              id: `pay_test_${Date.now().toString().slice(-6)}`,
              amount: 150000, // ₹1,500.00
              currency: "INR",
              status: "authorized",
              method: "upi",
              vpa: "customer@okhdfcbank",
              email: "shopper@example.com",
              contact: "+919876543210",
              notes: {
                purpose: "E-Commerce Purchase"
              },
              created_at: Math.floor(Date.now() / 1000)
            }
          }
        },
        created_at: Math.floor(Date.now() / 1000)
      };
      await postRazorpayWebhook(sampleRaw);
      await fetchEvents();
    } catch (err) {
      console.error('Failed to simulate raw webhook:', err);
    } finally {
      setSimulating(false);
    }
  };

  const handleSimulateEnrichedWebhook = async () => {
    setSimulating(true);
    try {
      const sampleEnriched = {
        entity: "event",
        account_id: "acc_rzp_test_merchant",
        event: "payment.authorized",
        contains: ["payment"],
        payload: {
          payment: {
            entity: {
              id: `pay_enr_${Date.now().toString().slice(-6)}`,
              amount: 28410050, // ₹284,100.50
              currency: "INR",
              status: "authorized",
              method: "upi",
              vpa: "compromised_user@okaxis",
              email: "victim@example.com",
              contact: "+919876512345",
              notes: {
                step: 452,
                type: "TRANSFER",
                oldbalanceOrg: 284100.50,
                oldbalanceDest: 0.00,
                nameOrig: "C_VICTIM_P0",
                nameDest: "C_MULE_P0",
                context_source: "ENRICHED_MERCHANT_ENVELOPE"
              },
              created_at: Math.floor(Date.now() / 1000)
            }
          }
        },
        created_at: Math.floor(Date.now() / 1000)
      };
      await postRazorpayWebhook(sampleEnriched);
      await fetchEvents();
    } catch (err) {
      console.error('Failed to simulate enriched webhook:', err);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl mt-8">
      {/* Header Banner */}
      <div className="p-5 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/30 border-b border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wide">
              Track 02 Integration
            </span>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              Razorpay Test Mode Webhook Monitor
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time external payment event ingestion, signature verification, and zero-fabrication model-readiness gating.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchEvents}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Feed
          </button>
          <button
            onClick={handleSimulateRawWebhook}
            disabled={simulating}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-colors flex items-center gap-1.5"
          >
            <ArrowDownRight className="w-3.5 h-3.5" />
            Dispatch Raw Event (₹1.5k)
          </button>
          <button
            onClick={handleSimulateEnrichedWebhook}
            disabled={simulating}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-colors flex items-center gap-1.5"
          >
            <Send className="w-3.5 h-3.5" />
            Dispatch Enriched Event (₹284k)
          </button>
        </div>
      </div>

      {/* Truth-Boundary Notice */}
      <div className="px-5 py-2.5 bg-slate-950/60 border-b border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lock className="w-3.5 h-3.5 text-indigo-400" />
          <span>
            <strong className="text-slate-300">Operational Boundary:</strong> Events are received via <code className="text-indigo-300">POST /v1/webhooks/razorpay</code> in Test Mode. Raw events without pre-transaction banking balance context are honestly gated with zero ML fabrication.
          </span>
        </div>
        <span className="text-slate-500 font-mono">HMAC-SHA256 Idempotent</span>
      </div>

      {/* Events Table / List */}
      <div className="overflow-x-auto">
        {events.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No webhook events received yet. Click "Dispatch Raw Event" or send a test webhook to <code className="text-slate-400">/v1/webhooks/razorpay</code>.
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Source & Payment ID</th>
                <th className="px-4 py-3">Event Type</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Model Readiness State</th>
                <th className="px-4 py-3">Risk Decision</th>
                <th className="px-4 py-3 text-right">Integrity Audit Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {events.map((ev) => {
                const isInsufficient = ev.evaluation_status === 'INSUFFICIENT_FEATURES_FOR_MODEL_EVALUATION';
                const isEnriched = ev.evaluation_status === 'EVALUATED_ENRICHED_TEST_MODE';

                return (
                  <tr key={ev.event_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300">
                          {ev.source}
                        </span>
                        <span className="font-mono font-bold text-white">{ev.payment_id}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                        {ev.method.toUpperCase()} • {ev.customer_contact_masked || ev.customer_vpa || 'Anonymous'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-slate-300 font-medium">{ev.event_type}</span>
                      <div className="text-[10px] text-slate-500">{new Date(ev.received_at_utc).toLocaleTimeString()}</div>
                    </td>
                    <td className="px-4 py-3 font-semibold text-white">
                      ₹{ev.amount_inr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3">
                      {isInsufficient ? (
                        <div>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            <AlertTriangle className="w-3 h-3" />
                            INSUFFICIENT FEATURES
                          </span>
                          <p className="text-[10px] text-slate-400 mt-1 max-w-xs leading-relaxed">
                            Received successfully. Model evaluation requires banking/context fields unavailable in the raw gateway event.
                          </p>
                        </div>
                      ) : isEnriched ? (
                        <div>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <CheckCircle2 className="w-3 h-3" />
                            TEST MODE — ENRICHED CONTEXT
                          </span>
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Model: {ev.engine_metadata?.model_version || 'v1.0.0-HGB'} | Policy: θ* = 0.990
                          </div>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-400">{ev.evaluation_status}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {ev.decision ? (
                        <div>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                            ev.decision === 'DECLINED' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                            ev.decision === 'REVIEW_REQUIRED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                            'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}>
                            {ev.action} ({ev.risk_score?.toFixed(4)})
                          </span>
                          {ev.audit_id && (
                            <div className="text-[9px] text-slate-500 font-mono mt-0.5 truncate max-w-[120px]">
                              {ev.audit_id}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-600 text-xs italic">N/A (Gated)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-1 rounded border border-slate-800">
                        {ev.integrity_hash.slice(0, 16)}...
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
