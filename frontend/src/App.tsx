import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { StreamPage } from './pages/StreamPage';
import { InspectorPage } from './pages/InspectorPage';
import { AuditPage } from './pages/AuditPage';
import { BenchmarksPage } from './pages/BenchmarksPage';
import { EvaluateResponse, HealthResponse } from './types/engine';
import { getHealth } from './api/client';

export function App() {
  const getInitialTab = (): string => {
    const path = window.location.pathname.replace('/', '').toLowerCase();
    if (path.startsWith('stream')) return 'stream';
    if (path.startsWith('inspector')) return 'inspector';
    if (path.startsWith('audit')) return 'audit';
    if (path.startsWith('benchmarks') || path.startsWith('research')) return 'benchmarks';
    return 'dashboard';
  };

  const [activeTab, setActiveTabState] = useState<string>(getInitialTab);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluateResponse | null>(null);
  const [recentEvaluations, setRecentEvaluations] = useState<EvaluateResponse[]>([]);

  const setActiveTab = (tab: string) => {
    setActiveTabState(tab);
    const newPath = tab === 'dashboard' ? '/' : `/${tab}`;
    if (window.location.pathname !== newPath) {
      window.history.pushState({ tab }, '', newPath);
    }
  };

  // Synchronize browser history (Back / Forward buttons)
  useEffect(() => {
    const handlePopState = () => {
      setActiveTabState(getInitialTab());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Check backend health on startup
  useEffect(() => {
    getHealth()
      .then((h) => setHealth(h))
      .catch((err) => console.log('Backend health standby:', err));
  }, []);

  const handleInspectTransaction = (response: EvaluateResponse) => {
    setSelectedEvaluation(response);
    setActiveTabState('inspector');
    window.history.pushState({ tab: 'inspector', txId: response.transaction_id }, '', `/inspector/${response.transaction_id}`);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Top Sticky Navbar */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} health={health} />

      {/* Main View Body */}
      <main className="flex-1">
        {activeTab === 'dashboard' && (
          <DashboardPage
            onNavigateToStream={() => setActiveTab('stream')}
            health={health}
          />
        )}

        {activeTab === 'stream' && (
          <StreamPage
            onInspectTransaction={handleInspectTransaction}
            recentEvaluations={recentEvaluations}
            setRecentEvaluations={setRecentEvaluations}
          />
        )}

        {activeTab === 'inspector' && (
          <InspectorPage
            evaluation={selectedEvaluation}
            onBack={() => setActiveTab('stream')}
          />
        )}

        {activeTab === 'audit' && <AuditPage />}

        {activeTab === 'benchmarks' && <BenchmarksPage />}
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 py-6 text-xs font-mono text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">Risk Sentinel</span>
            <span>•</span>
            <span>{health?.engine_version || 'v2.8.0-prod'}</span>
            <span>•</span>
            <span className="text-emerald-400">Decision Engine UI</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <span>Local Benchmark: p99 2.40 ms</span>
            <span>•</span>
            <span>Target Budget: 35.0 ms</span>
            <span>•</span>
            <span>Defensive Fraud Track</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
