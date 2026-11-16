import React, { useState } from 'react';
import { getStoredConfig, saveStoredConfig, resetStoredConfig, checkHealth } from '../../services/api';
import type { ApiConfig } from '../../types/api';
import { XIcon, ServerIcon, CheckIcon, AlertTriangleIcon, RefreshCwIcon } from '../common/Icons';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigChanged: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onConfigChanged }) => {
  const [config, setConfig] = useState<ApiConfig>(getStoredConfig());
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState<string>('');
  const [testPing, setTestPing] = useState<number | null>(null);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTestStatus('testing');
    setTestMessage('');
    try {
      // Temporarily save to test with the current form values
      saveStoredConfig(config);
      const { data, pingMs } = await checkHealth();
      setTestStatus('success');
      setTestPing(pingMs);
      setTestMessage(`Connected to ${data.status.toUpperCase()} (${data.companies} companies, LLM: ${data.llm || 'configured'})`);
      onConfigChanged();
    } catch (err: unknown) {
      setTestStatus('error');
      setTestMessage(err instanceof Error ? err.message : 'Connection failed');
    }
  };

  const handleSave = () => {
    saveStoredConfig(config);
    onConfigChanged();
    onClose();
  };

  const handleReset = () => {
    const def = resetStoredConfig();
    setConfig(def);
    setTestStatus('idle');
    setTestMessage('');
    onConfigChanged();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-2 text-slate-100 font-semibold text-base">
            <ServerIcon className="w-5 h-5 text-emerald-400" />
            <span>API & Connection Settings</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-md hover:bg-slate-800 transition-colors"
          >
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 text-sm">
          <div>
            <label className="block text-xs font-mono font-medium text-slate-400 mb-1.5 uppercase tracking-wider">
              API Base URL (FastAPI Endpoint)
            </label>
            <div className="relative">
              <input
                type="text"
                value={config.baseUrl}
                onChange={(e) => {
                  setConfig({ ...config, baseUrl: e.target.value });
                  setTestStatus('idle');
                }}
                placeholder="http://32.236.49.234:8000"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2.5 text-slate-100 font-mono text-xs focus:outline-hidden focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={() => setConfig({ ...config, baseUrl: 'http://32.236.49.234:8000' })}
                className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                AWS EC2 Default
              </button>
              <button
                type="button"
                onClick={() => setConfig({ ...config, baseUrl: 'http://localhost:8000' })}
                className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Localhost:8000
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-medium text-slate-400 mb-1.5 uppercase tracking-wider">
              X-API-Key Header
            </label>
            <input
              type="text"
              value={config.apiKey}
              onChange={(e) => {
                setConfig({ ...config, apiKey: e.target.value });
                setTestStatus('idle');
              }}
              placeholder="SECTRA@Nitish"
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2.5 text-slate-100 font-mono text-xs focus:outline-hidden focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Sent as <code className="text-slate-400 font-mono">X-API-Key</code> to authenticate against protected <code className="text-slate-400 font-mono">/ask</code> endpoints.
            </p>
          </div>

          {/* Test connection alert */}
          {testStatus !== 'idle' && (
            <div
              className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
                testStatus === 'success'
                  ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
                  : testStatus === 'error'
                  ? 'bg-rose-950/40 border-rose-800 text-rose-300'
                  : 'bg-slate-800/60 border-slate-700 text-slate-300'
              }`}
            >
              {testStatus === 'success' && <CheckIcon className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />}
              {testStatus === 'error' && <AlertTriangleIcon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />}
              {testStatus === 'testing' && <RefreshCwIcon className="w-4 h-4 text-slate-400 shrink-0 mt-0.5 animate-spin" />}
              <div className="flex-1">
                <div className="font-medium flex items-center justify-between">
                  <span>
                    {testStatus === 'success' ? 'Connected Successfully' : testStatus === 'error' ? 'Connection Error' : 'Testing Connectivity...'}
                  </span>
                  {testPing !== null && <span className="font-mono text-[10px]">{testPing} ms</span>}
                </div>
                {testMessage && <p className="mt-0.5 font-mono text-[11px] text-slate-300">{testMessage}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/50">
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Reset to Defaults
          </button>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleTest}
              disabled={testStatus === 'testing'}
              className="px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-slate-200 font-medium text-xs flex items-center gap-1.5 transition-colors"
            >
              <RefreshCwIcon className={`w-3.5 h-3.5 ${testStatus === 'testing' ? 'animate-spin' : ''}`} />
              <span>Test Connection</span>
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
