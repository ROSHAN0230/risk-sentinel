import React from 'react';
import { DecisionEnum, ActionEnum } from '../types/engine';
import { CheckCircle2, AlertTriangle, Eye, XCircle } from 'lucide-react';

interface DecisionProps {
  decision: DecisionEnum;
  action?: ActionEnum;
  size?: 'sm' | 'md' | 'lg';
}

export const DecisionBadge: React.FC<DecisionProps> = ({ decision, action, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3.5 py-1.5 text-sm font-semibold'
  };

  switch (decision) {
    case 'APPROVED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${sizeClasses[size]}`}>
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>APPROVE</span>
        </span>
      );
    case 'CHALLENGED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30 ${sizeClasses[size]}`}>
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>STEP-UP 2FA</span>
        </span>
      );
    case 'REVIEW_REQUIRED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-mono bg-yellow-500/10 text-yellow-300 border border-yellow-500/30 ${sizeClasses[size]}`}>
          <Eye className="w-3.5 h-3.5" />
          <span>MANUAL REVIEW</span>
        </span>
      );
    case 'DECLINED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-mono bg-red-500/15 text-red-400 border border-red-500/40 ${sizeClasses[size]}`}>
          <XCircle className="w-3.5 h-3.5" />
          <span>DECLINE</span>
        </span>
      );
  }
};
