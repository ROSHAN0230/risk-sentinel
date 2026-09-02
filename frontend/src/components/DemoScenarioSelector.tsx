import React from 'react';
import { DEMO_FIXTURES } from '../api/client';
import { DemoFixture } from '../types/engine';
import { Play, Sparkles } from 'lucide-react';

interface Props {
  selectedDemoId: string | null;
  onSelectDemo: (fixture: DemoFixture) => void;
  isLoading: boolean;
}

export const DemoScenarioSelector: React.FC<Props> = ({ selectedDemoId, onSelectDemo, isLoading }) => {
  return (
    <div className="p-5 rounded-xl bg-slate-800/90 border border-slate-700 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-100">Live Demo Scenario Launcher (9 Scenarios)</h3>
        </div>
        <span className="text-xs font-mono text-amber-400/90 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
          Judge & Viva Presets
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {DEMO_FIXTURES.map((fixture) => {
          const isSelected = selectedDemoId === fixture.id;
          return (
            <button
              key={fixture.id}
              onClick={() => onSelectDemo(fixture)}
              disabled={isLoading}
              className={`p-3 rounded-lg text-left transition-all flex flex-col justify-between border ${
                isSelected
                  ? 'bg-blue-600/20 border-blue-500 text-white shadow-sm'
                  : 'bg-slate-900/80 border-slate-700/80 text-slate-300 hover:border-slate-500 hover:bg-slate-800'
              } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono font-bold text-blue-400">{fixture.id}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 border border-slate-700 text-slate-400">
                  {fixture.expected_decision}
                </span>
              </div>
              <span className="text-xs font-medium text-slate-100 line-clamp-1 mb-1">{fixture.title}</span>
              <p className="text-[11px] text-slate-400 line-clamp-2">{fixture.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
