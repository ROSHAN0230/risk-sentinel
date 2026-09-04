import React, { useState } from 'react';
import { Shield, Activity, Database, FileText, Cpu, Menu, X } from 'lucide-react';
import { HealthResponse } from '../types/engine';

interface Props {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  health: HealthResponse | null;
}

export const Navbar: React.FC<Props> = ({ activeTab, setActiveTab, health }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isHealthy = health?.status === 'HEALTHY';
  const engineVer = health?.engine_version || 'v2.8.0-prod';

  const navItems = [
    { id: 'dashboard', label: 'Executive Dashboard' },
    { id: 'stream', label: 'Live Stream & Demo' },
    { id: 'inspector', label: 'Investigation Workspace' },
    { id: 'audit', label: 'Audit Ledger' },
    { id: 'benchmarks', label: 'Research Forensics' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer shrink-0 select-none"
            onClick={() => {
              setActiveTab('dashboard');
              setMobileMenuOpen(false);
            }}
          >
            <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 shrink-0">
              <Shield className="w-6 h-6" />
            </div>
            <div className="flex flex-col justify-center">
              <div className="flex items-center gap-2.5">
                <span className="font-bold text-base sm:text-lg text-slate-100 tracking-tight whitespace-nowrap">
                  Risk Sentinel
                </span>
                <span className="text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded-md bg-blue-500/20 text-blue-300 border border-blue-500/30 whitespace-nowrap tracking-wider shadow-sm">
                  {engineVer.toUpperCase()}
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-400 font-mono tracking-tight whitespace-nowrap">
                Causal AI Risk Decision Engine
              </p>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-800/80 p-1 rounded-xl border border-slate-700 shrink-0">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`px-2.5 lg:px-3 py-1.5 rounded-lg text-xs lg:text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === item.id
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-700/60'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {/* System Telemetry Badges */}
          <div className="hidden lg:flex items-center gap-2.5 shrink-0">
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs font-mono">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></span>
              <span className="text-slate-400">Engine:</span>
              <span className={isHealthy ? 'text-emerald-400 font-semibold' : 'text-red-400'}>
                {health ? health.status : 'STANDBY'}
              </span>
            </div>

            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 text-xs font-mono text-blue-300">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span className="hidden xl:inline">Model B Champion</span>
              <span className="hidden xl:inline text-slate-500">|</span>
              <span className="text-slate-300">Target Budget: 35 ms</span>
            </div>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-900 border-b border-slate-700 px-4 py-3 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id);
                setMobileMenuOpen(false);
              }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === item.id
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              {item.label}
            </button>
          ))}
          <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-xs font-mono text-slate-400">
            <span>Engine: {isHealthy ? 'HEALTHY' : 'STANDBY'}</span>
            <span>Budget: 35 ms</span>
          </div>
        </div>
      )}
    </header>
  );
};
