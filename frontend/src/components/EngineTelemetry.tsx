import React from 'react';
import { EngineMetadata } from '../types/engine';
import { Cpu, Zap, Shield, GitCommit, Target } from 'lucide-react';

interface Props {
  metadata: EngineMetadata;
}

export const EngineTelemetry: React.FC<Props> = ({ metadata }) => {
  const isFallback = metadata.fallback_triggered;

  return (
    <div className="p-4 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
      <div className="flex items-center gap-2">
        <Cpu className="w-4 h-4 text-blue-400" />
        <span className="text-slate-400">Active Model:</span>
        <span className={`font-semibold px-2 py-0.5 rounded ${isFallback ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40' : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'}`}>
          {metadata.model_type}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-400" />
        <span className="text-slate-400">Response Latency:</span>
        <span className="text-white font-semibold">{metadata.execution_latency_ms.toFixed(2)} ms</span>
      </div>

      <div className="flex items-center gap-2">
        <Target className="w-4 h-4 text-blue-400" />
        <span className="text-slate-400">Target Budget:</span>
        <span className="text-slate-300">35.0 ms</span>
      </div>

      <div className="flex items-center gap-2">
        <Shield className="w-4 h-4 text-emerald-400" />
        <span className="text-slate-400">Threshold:</span>
        <span className="text-white font-semibold">θ* = {metadata.operating_threshold.toFixed(3)}</span>
      </div>

      <div className="flex items-center gap-2">
        <GitCommit className="w-4 h-4 text-slate-400" />
        <span className="text-slate-400">Engine:</span>
        <span className="text-slate-300">{metadata.engine_version}</span>
      </div>
    </div>
  );
};
