import React from 'react';
import type { HealthResponse } from '../../types/api';
import { SettingsIcon, TerminalIcon, BookOpenIcon, LayersIcon, BarChart3Icon } from '../common/Icons';

export type NavTab = 'overview' | 'demo' | 'architecture' | 'benchmarks';

interface HeaderProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  health: HealthResponse | null;
  healthPing: number | null;
  healthLoading: boolean;
  onOpenSettings: () => void;
  onRefreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  health,
  healthPing,
  healthLoading,
  onOpenSettings,
}) => {
  const isHealthy = health?.status === 'ok';

  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview & Data', icon: <BookOpenIcon className="w-3.5 h-3.5" /> },
    { id: 'demo', label: 'Research Terminal', icon: <TerminalIcon className="w-3.5 h-3.5" /> },
    { id: 'architecture', label: 'Architecture & Safety', icon: <LayersIcon className="w-3.5 h-3.5" /> },
    { id: 'benchmarks', label: 'Benchmarks & Eval', icon: <BarChart3Icon className="w-3.5 h-3.5" /> },
  ];

  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-mono font-bold text-sm tracking-wider shadow-inner">
              SEC
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold tracking-tight text-slate-100 text-base">
                  S.E.C.T.R.A
                </span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                  v0.1.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block truncate max-w-xs md:max-w-md">
                SEC EDGAR 10-K Quantitative & Narrative Intelligence
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800 text-emerald-400 shadow-xs border border-slate-700/70'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Action: Health Status & Settings */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={onOpenSettings}
              className={`flex items-center gap-2 px-2.5 py-1 rounded-full border text-xs font-mono transition-colors ${
                isHealthy
                  ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300 hover:bg-emerald-950/70'
                  : healthLoading
                  ? 'bg-slate-900 border-slate-700 text-slate-400'
                  : 'bg-rose-950/40 border-rose-800/60 text-rose-300 hover:bg-rose-950/70'
              }`}
              title="Click to view API settings or switch endpoints"
            >
              <span className="relative flex h-2 w-2">
                {isHealthy && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                )}
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    isHealthy ? 'bg-emerald-400' : healthLoading ? 'bg-amber-400' : 'bg-rose-500'
                  }`}
                ></span>
              </span>
              <span className="hidden sm:inline">
                {isHealthy
                  ? `LIVE ${healthPing ? `(${healthPing}ms)` : ''}`
                  : healthLoading
                  ? 'CONNECTING...'
                  : 'OFFLINE'}
              </span>
              {isHealthy && health?.companies && (
                <span className="text-[10px] text-emerald-500/80 border-l border-emerald-800/60 pl-1.5 hidden lg:inline">
                  {health.companies} CO
                </span>
              )}
            </button>

            <button
              onClick={onOpenSettings}
              className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title="API Configuration"
            >
              <SettingsIcon className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile Navigation Tabs */}
        <div className="flex md:hidden overflow-x-auto py-2 gap-1 border-t border-slate-800/60">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
                  isActive
                    ? 'bg-slate-800 text-emerald-400 border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
