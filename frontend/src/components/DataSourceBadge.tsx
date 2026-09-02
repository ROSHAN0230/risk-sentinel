import React from 'react';
import { Activity, BookOpen, Sparkles } from 'lucide-react';

export type DataSourceType = 'LIVE_ENGINE' | 'BENCHMARK_RESEARCH' | 'DEMO_SCENARIO';

interface Props {
  source: DataSourceType;
  className?: string;
  size?: 'sm' | 'md';
}

export const DataSourceBadge: React.FC<Props> = ({ source, className = '', size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  switch (source) {
    case 'LIVE_ENGINE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-mono font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30 ${sizeClasses} ${className}`}
          title="Directly sourced from active FastAPI decision engine runtime"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
          <span>Live Engine</span>
        </span>
      );
    case 'BENCHMARK_RESEARCH':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-mono font-medium bg-purple-500/10 text-purple-300 border border-purple-500/30 ${sizeClasses} ${className}`}
          title="Academic research findings from PaySim held-out test split (steps 378–743)"
        >
          <BookOpen className="w-3 h-3 text-purple-400" />
          <span>Benchmark / Research</span>
        </span>
      );
    case 'DEMO_SCENARIO':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-mono font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30 ${sizeClasses} ${className}`}
          title="Pre-configured test fixture for interactive judge evaluation"
        >
          <Sparkles className="w-3 h-3 text-amber-400" />
          <span>Demo Scenario</span>
        </span>
      );
  }
};
