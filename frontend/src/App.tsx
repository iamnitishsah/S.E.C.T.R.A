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
    // Periodically refresh health status every 45s
    const interval = setInterval(refreshHealth, 45000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Persistent Navigation Header */}
      <Header
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        health={health}
        healthPing={healthPing}
        healthLoading={healthLoading}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onRefreshHealth={refreshHealth}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {activeTab === 'overview' && <OverviewPage />}
        {activeTab === 'demo' && <DemoPage />}
        {activeTab === 'architecture' && <ArchitecturePage />}
        {activeTab === 'benchmarks' && <BenchmarksPage />}
      </main>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onConfigChanged={refreshHealth}
      />

      {/* Institutional Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-8 text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-bold text-slate-400">S.E.C.T.R.A</span>
            <span>•</span>
            <span>Securities & Exchange Commission Tracking, Retrieval & Analysis</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>20 Companies</span>
            <span>•</span>
            <span>80 Annual 10-K Reports</span>
            <span>•</span>
            <span>Zero-Hallucination Tripartite Architecture</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
