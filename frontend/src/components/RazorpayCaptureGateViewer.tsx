import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, ArrowRight, CheckCircle2, XCircle, RefreshCw, Layers } from 'lucide-react';
import { CaptureGateResult } from '../types/engine';
import { evaluateAndCaptureGate, getCaptureGateEvents } from '../api/client';

export const RazorpayCaptureGateViewer: React.FC = () => {
  const [events, setEvents] = useState<CaptureGateResult[]>([]);
  const [activeEvent, setActiveEvent] = useState<CaptureGateResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchEvents = async () => {
    try {
      const data = await getCaptureGateEvents(10);
      setEvents(data);
      if (data.length > 0 && !activeEvent) {
        setActiveEvent(data[0]);
      }
    } catch (err) {
      console.error('Failed to load capture gate events:', err);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const triggerBenignFlow = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      const payId = `pay_test_${Math.random().toString(36).substring(2, 9)}`;
      const res = await evaluateAndCaptureGate({
        payment_id: payId,
        order_id: `order_${payId.replace('pay_', '')}`,
        amount_paise: 8450, // 84.50 INR
        currency: 'INR',
        status: 'authorized',
        method: 'upi',
        contact: '9876543210',
        notes: {
          step: '450',
          type: 'PAYMENT',
          oldbalanceOrg: '15000.00',
          oldbalanceDest: '25000.00',
          nameOrig: 'C_BENIGN_CONSUMER',
          nameDest: 'M_VERIFIED_MERCHANT'
        }
      });
      setActiveEvent(res);
      setFeedback(`Payment ${payId} evaluated: APPROVED -> Capture API called -> CAPTURED`);
      await fetchEvents();
    } catch (err: any) {
      setFeedback(`Error: ${err.message || 'Execution failed'}`);
    } finally {
      setLoading(false);
    }
  };

  const triggerDrainFlow = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      const payId = `pay_test_${Math.random().toString(36).substring(2, 9)}`;
      const res = await evaluateAndCaptureGate({
        payment_id: payId,
        order_id: `order_${payId.replace('pay_', '')}`,
        amount_paise: 28410050, // 284,100.50 INR
        currency: 'INR',
        status: 'authorized',
        method: 'upi',
        notes: {
          step: '452',
          type: 'TRANSFER',
          oldbalanceOrg: '284100.50',
          oldbalanceDest: '0.00',
          nameOrig: 'C_VICTIM_DRAIN',
          nameDest: 'C_MULE_ACCOUNT'
        }
      });
      setActiveEvent(res);
      setFeedback(`Payment ${payId} evaluated: DECLINED -> Capture SUPPRESSED -> HELD`);
      await fetchEvents();
    } catch (err: any) {
      setFeedback(`Error: ${err.message || 'Execution failed'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 my-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-semibold text-white tracking-wide">
              Razorpay Capture Gate <span className="text-xs font-normal px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">Phase 1</span>
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Merchant-Controlled Risk Gate: Evaluates payments in <code className="text-amber-400">AUTHORIZED</code> state before executing Razorpay manual capture.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={triggerBenignFlow}
            disabled={loading}
            className="px-3 py-1.5 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-700 text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Dispatch benign authorized payment (Approved -> Captured)"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Test Flow A (Approve & Capture)
          </button>
          <button
            onClick={triggerDrainFlow}
            disabled={loading}
            className="px-3 py-1.5 rounded bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-700 text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Dispatch 100% balance drain (Declined -> Capture Suppressed -> Held)"
          >
            <XCircle className="w-3.5 h-3.5" />
            Test Flow B (Hold & Block Capture)
          </button>
          <button
            onClick={fetchEvents}
            disabled={loading}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh events"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {feedback && (
        <div className="mt-3 p-2 text-xs rounded bg-slate-800 text-slate-200 border border-slate-700 font-mono">
          {feedback}
        </div>
      )}

      {/* Active Inspection Dossier */}
      {activeEvent && (
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 bg-slate-950 p-4 rounded-lg border border-slate-800">
          <div className="col-span-2">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">PAYMENT ID</span>
            <span className="text-xs font-mono font-medium text-slate-200 truncate block mt-0.5">{activeEvent.payment_id}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">STATE BEFORE</span>
            <span className="inline-block px-1.5 py-0.5 mt-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800">
              {activeEvent.payment_status_before.toUpperCase()}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">RISK SCORE</span>
            <span className="text-xs font-mono font-bold text-slate-200 block mt-0.5">
              {activeEvent.risk_score !== null && activeEvent.risk_score !== undefined ? activeEvent.risk_score.toFixed(4) : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">DECISION</span>
            <span className={`inline-block px-1.5 py-0.5 mt-0.5 text-[10px] font-mono font-bold rounded ${
              activeEvent.decision === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
              activeEvent.decision === 'DECLINED' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
              'bg-slate-800 text-slate-300 border border-slate-700'
            }`}>
              {activeEvent.decision || 'NOT_EVALUATED'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">CAPTURE ACTION</span>
            <span className={`inline-block px-1.5 py-0.5 mt-0.5 text-[10px] font-mono rounded ${
              activeEvent.capture_action === 'CAPTURE_CALLED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
              'bg-slate-800 text-slate-400 border border-slate-700'
            }`}>
              {activeEvent.capture_action}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">FINAL RESULT</span>
            <span className={`inline-block px-1.5 py-0.5 mt-0.5 text-[10px] font-mono font-bold rounded ${
              activeEvent.capture_status === 'CAPTURED' ? 'bg-emerald-900 text-emerald-200 border border-emerald-700' :
              'bg-amber-950 text-amber-300 border border-amber-800'
            }`}>
              {activeEvent.capture_status}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">PROVENANCE</span>
            <span className="inline-block px-1.5 py-0.5 mt-0.5 text-[9px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
              {activeEvent.provenance}
            </span>
          </div>
        </div>
      )}

      {/* Events Stream Table */}
      {events.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[10px]">
                <th className="py-2 px-2">TIME</th>
                <th className="py-2 px-2">PAYMENT ID</th>
                <th className="py-2 px-2">AMOUNT</th>
                <th className="py-2 px-2">SCORE</th>
                <th className="py-2 px-2">DECISION</th>
                <th className="py-2 px-2">CAPTURE STATUS</th>
                <th className="py-2 px-2">REASON</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {events.map((ev) => (
                <tr
                  key={ev.gate_event_id}
                  onClick={() => setActiveEvent(ev)}
                  className={`hover:bg-slate-850/60 cursor-pointer transition-colors ${
                    activeEvent?.gate_event_id === ev.gate_event_id ? 'bg-slate-800/80' : ''
                  }`}
                >
                  <td className="py-2 px-2 text-slate-400 text-[11px] whitespace-nowrap">
                    {ev.timestamp_utc.split('T')[1]?.substring(0, 8)}
                  </td>
                  <td className="py-2 px-2 text-slate-200 font-medium">{ev.payment_id}</td>
                  <td className="py-2 px-2 text-slate-300">₹{ev.amount_inr.toFixed(2)}</td>
                  <td className="py-2 px-2 text-slate-300">
                    {ev.risk_score !== null && ev.risk_score !== undefined ? ev.risk_score.toFixed(4) : '-'}
                  </td>
                  <td className="py-2 px-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      ev.decision === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                      ev.decision === 'DECLINED' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {ev.decision || 'N/A'}
                    </span>
                  </td>
                  <td className="py-2 px-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      ev.capture_status === 'CAPTURED' ? 'bg-emerald-900 text-emerald-200 border border-emerald-700' :
                      'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {ev.capture_status}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-slate-400 text-[11px] truncate max-w-[140px]">
                    {ev.primary_reason_code || 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
