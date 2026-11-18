import React, { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import type { NavTab } from './components/layout/Header';
import { SettingsModal } from './components/layout/SettingsModal';
import { OverviewPage } from './pages/OverviewPage';
import { DemoPage } from './pages/DemoPage';
import { ArchitecturePage } from './pages/ArchitecturePage';
import { BenchmarksPage } from './pages/BenchmarksPage';
import { checkHealth } from './services/api';
import type { HealthResponse } from './types/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthPing, setHealthPing] = useState<number | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  const refreshHealth = async () => {
    setHealthLoading(true);
    try {
      const { data, pingMs } = await checkHealth();
      setHealth(data);
      setHealthPing(pingMs);
    } catch {
      setHealth(null);
      setHealthPing(null);
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 45000);
    return () => clearInterval(interval);
  }, []);

  const goTo = (tab: NavTab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col">
      <Header
        activeTab={activeTab}
        onTabChange={goTo}
        health={health}
        healthPing={healthPing}
        healthLoading={healthLoading}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onRefreshHealth={refreshHealth}
      />

      <main className="flex-1 w-full max-w-6xl mx-auto px-5 sm:px-8 pt-12 pb-24">
        {activeTab === 'overview' && <OverviewPage onNavigate={goTo} />}
        {activeTab === 'demo' && <DemoPage />}
        {activeTab === 'architecture' && <ArchitecturePage />}
        {activeTab === 'benchmarks' && <BenchmarksPage />}
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onConfigChanged={refreshHealth}
      />

      <footer className="border-t border-rule">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 py-6 flex flex-col sm:flex-row gap-2 sm:items-center justify-between text-xs text-muted">
          <span>
            <span className="font-medium text-ink-2">S.E.C.T.R.A</span> — Securities &amp; Exchange Commission
            Tracking, Retrieval &amp; Analysis
          </span>
          <span>Data from SEC EDGAR. Not investment advice.</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
