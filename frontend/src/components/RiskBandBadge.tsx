import React from 'react';
import { RiskBand } from '../types/engine';

interface Props {
  band: RiskBand;
  score?: number;
}

export const RiskBandBadge: React.FC<Props> = ({ band, score }) => {
  switch (band) {
    case 'LOW_RISK':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          LOW_RISK {score !== undefined && `(${score.toFixed(4)})`}
        </span>
      );
    case 'MEDIUM_RISK':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          MEDIUM_RISK {score !== undefined && `(${score.toFixed(4)})`}
        </span>
      );
    case 'HIGH_RISK':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-red-500/15 text-red-400 border border-red-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
          HIGH_RISK {score !== undefined && `(${score.toFixed(4)})`}
        </span>
      );
  }
};
