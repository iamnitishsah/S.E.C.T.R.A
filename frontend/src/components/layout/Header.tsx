import React from 'react';
import type { HealthResponse } from '../../types/api';
import { SettingsIcon } from '../common/Icons';

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

  const navItems: { id: NavTab; label: string }[] = [
    { id: 'overview', label: 'Overview & Data' },
    { id: 'demo', label: 'Research Terminal' },
    { id: 'architecture', label: 'System Architecture' },
    { id: 'benchmarks', label: 'Evaluation & Benchmarks' },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#0c0e12]/95 backdrop-blur-xs border-b border-neutral-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo & Product Name */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => onTabChange('overview')}
              className="flex items-center gap-2.5 text-left group cursor-pointer"
            >
              <img
                src="/logo.png"
                alt="S.E.C.T.R.A"
                className="w-7 h-7 rounded object-contain border border-neutral-800 bg-neutral-900"
              />
              <span className="font-mono font-bold tracking-tight text-white text-base">
                S.E.C.T.R.A
              </span>
              <span className="text-neutral-600 hidden sm:inline">|</span>
              <span className="text-xs text-neutral-400 hidden sm:inline group-hover:text-neutral-300 transition-colors">
                SEC 10-K Research & Analysis
              </span>
            </button>
          </div>

          {/* Desktop Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`px-3 py-1.5 rounded-md text-xs transition-colors ${
                    isActive
                      ? 'bg-neutral-800 text-white font-medium shadow-xs'
                      : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/40'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Right Action: Connection Status & API Key */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-[11px] font-mono text-neutral-400">
              <span
                className={`w-2 h-2 rounded-full ${
                  isHealthy ? 'bg-emerald-500' : healthLoading ? 'bg-amber-500' : 'bg-rose-500'
                }`}
              />
              <span className="hidden sm:inline text-neutral-300">
                {isHealthy ? 'API Online' : healthLoading ? 'Checking...' : 'API Offline'}
              </span>
              {isHealthy && healthPing !== null && (
                <span className="text-neutral-500 hidden lg:inline">({healthPing}ms)</span>
              )}
            </div>

            <button
              onClick={onOpenSettings}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border border-neutral-700 bg-neutral-800/70 hover:bg-neutral-700/70 text-neutral-200 transition-colors"
              title="Configure API Key"
            >
              <SettingsIcon className="w-3.5 h-3.5 text-neutral-400" />
              <span>Key Settings</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation Tabs */}
        <div className="flex md:hidden overflow-x-auto py-2 gap-1 border-t border-neutral-800/80 scrollbar-none">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`px-2.5 py-1 rounded text-xs whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-neutral-800 text-white font-medium'
                    : 'text-neutral-400 hover:text-neutral-200'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
