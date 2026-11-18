import React from 'react';
import type { HealthResponse } from '../../types/api';

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

const NAV_ITEMS: { id: NavTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'demo', label: 'Ask' },
  { id: 'architecture', label: 'How it works' },
  { id: 'benchmarks', label: 'Evaluation' },
];

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  health,
  healthPing,
  healthLoading,
  onOpenSettings,
  onRefreshHealth,
}) => {
  const isHealthy = health?.status === 'ok';
  const status = isHealthy ? 'Online' : healthLoading ? 'Connecting' : 'Offline';
  const dot = isHealthy ? 'bg-accent' : healthLoading ? 'bg-faint animate-pulse' : 'bg-danger';

  const navButton = (item: { id: NavTab; label: string }) => {
    const isActive = activeTab === item.id;
    return (
      <button
        key={item.id}
        onClick={() => onTabChange(item.id)}
        aria-current={isActive ? 'page' : undefined}
        className={`relative px-3 py-2 text-sm whitespace-nowrap transition-colors ${
          isActive ? 'text-ink' : 'text-muted hover:text-ink'
        }`}
      >
        {item.label}
        {isActive && <span className="absolute left-3 right-3 -bottom-px h-px bg-ink" />}
      </button>
    );
  };

  return (
    <header className="sticky top-0 z-40 bg-bg/85 backdrop-blur-md border-b border-rule">
      <div className="max-w-[1680px] mx-auto px-6 sm:px-10 lg:px-16">
        <div className="flex items-center justify-between h-16 gap-6">
          <button onClick={() => onTabChange('overview')} className="flex items-center gap-2.5 shrink-0">
            <img src="/logo.png" alt="" className="w-6 h-6 rounded-md object-contain" />
            <span className="font-semibold tracking-tight text-base">S.E.C.T.R.A</span>
          </button>

          <nav className="hidden md:flex items-center self-stretch">{NAV_ITEMS.map(navButton)}</nav>

          <div className="flex items-center gap-4 text-sm">
            <button
              onClick={onRefreshHealth}
              className="flex items-center gap-2 text-muted hover:text-ink transition-colors"
              title={health?.llm ? `Model: ${health.llm}` : 'Check API status'}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
              <span className="hidden sm:inline">{status}</span>
              {isHealthy && healthPing !== null && (
                <span className="hidden lg:inline font-mono text-xs text-faint tabular">{healthPing} ms</span>
              )}
            </button>
            <button
              onClick={onOpenSettings}
              className="px-3 py-1.5 rounded-md border border-rule-strong text-ink-2 hover:text-ink hover:bg-surface transition-colors"
            >
              API key
            </button>
          </div>
        </div>

        <nav className="flex md:hidden -mx-3 overflow-x-auto pb-1">{NAV_ITEMS.map(navButton)}</nav>
      </div>
    </header>
  );
};
