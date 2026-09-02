import React from 'react';
import { AlertCircle, Shield } from 'lucide-react';

interface Props {
  className?: string;
}

export const DisclaimerBanner: React.FC<Props> = ({ className = '' }) => {
  return (
    <div className={`p-4 rounded-xl bg-slate-800/95 border border-slate-700 text-xs font-mono text-slate-300 flex items-start gap-3.5 ${className}`}>
      <Shield className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
      <div className="flex flex-col gap-1.5">
        <span className="font-bold text-slate-200 uppercase tracking-wider text-[11px]">
          Engineering & Compliance Truth Boundaries
        </span>
        <ul className="list-disc pl-4 space-y-1 text-slate-400">
          <li>
            <strong className="text-slate-300">Operating Risk Score (θ* = 0.990)</strong>: Calibrated decision score derived from balanced loss minimization (+7.106 log-odds shift, ~7.51% calibrated risk), not an uncalibrated probability statement.
          </li>
          <li>
            <strong className="text-slate-300">Latency Budgets</strong>: Local engine benchmark p99 is 2.40 ms (In-Process) / &lt;10 ms (REST); gateway target SLA budget is 35.0 ms.
          </li>
          <li>
            <strong className="text-slate-300">PaySim Research Observations</strong>: 99.99% dollars protected and channel bypass (PAYMENT/DEBIT) are academic dataset findings on PaySim held-out steps 378–743, not proprietary Razorpay live production KPIs.
          </li>
        </ul>
      </div>
    </div>
  );
};
