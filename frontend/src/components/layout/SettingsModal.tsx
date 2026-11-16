import React, { useState } from 'react';
import { getStoredApiKey, saveStoredApiKey, resetStoredApiKey, checkHealth, API_BASE_URL } from '../../services/api';
import { XIcon, CheckIcon, AlertTriangleIcon, RefreshCwIcon, ShieldCheckIcon } from '../common/Icons';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigChanged: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onConfigChanged }) => {
  const [apiKey, setApiKey] = useState<string>(getStoredApiKey());
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState<string>('');
  const [testPing, setTestPing] = useState<number | null>(null);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTestStatus('testing');
    setTestMessage('');
    try {
      saveStoredApiKey(apiKey);
      const { data, pingMs } = await checkHealth();
      setTestStatus('success');
      setTestPing(pingMs);
      setTestMessage(`Server Online: ${data.companies} companies loaded, Model: ${data.llm || 'configured'}`);
      onConfigChanged();
    } catch (err: unknown) {
      setTestStatus('error');
      setTestMessage(err instanceof Error ? err.message : 'Connection failed');
    }
  };

  const handleSave = () => {
    saveStoredApiKey(apiKey);
    onConfigChanged();
    onClose();
  };

  const handleReset = () => {
    const def = resetStoredApiKey();
    setApiKey(def);
    setTestStatus('idle');
    setTestMessage('');
    onConfigChanged();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-md bg-[#13161c] border border-neutral-800 rounded-xl shadow-xl overflow-hidden text-neutral-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-800 bg-[#0f1116]">
          <div className="flex items-center gap-2">
            <ShieldCheckIcon className="w-4 h-4 text-neutral-300" />
            <h3 className="text-sm font-semibold text-neutral-100">API Access Authentication</h3>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-200 p-1 rounded hover:bg-neutral-800/60 transition-colors"
          >
            <XIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Read-only Server Endpoint */}
          <div>
            <label className="block text-[11px] font-medium text-neutral-400 mb-1">
              Backend Endpoint
            </label>
            <div className="px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300 font-mono text-[11px] truncate select-all">
              {API_BASE_URL}
            </div>
            <p className="text-[10px] text-neutral-500 mt-1">
              Configured via deployment environment variables.
            </p>
          </div>

          {/* Editable API Key */}
          <div>
            <label className="block text-[11px] font-medium text-neutral-300 mb-1">
              X-API-Key Header
            </label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestStatus('idle');
              }}
              placeholder="e.g. SECTRA@Nitish"
              className="w-full bg-[#0a0c10] border border-neutral-700/80 rounded-lg px-3 py-2 text-neutral-100 font-mono text-xs focus:outline-hidden focus:border-neutral-500 transition-colors"
            />
            <p className="text-[10px] text-neutral-500 mt-1">
              Passed on every research query to authorize access against the backend.
            </p>
          </div>

          {/* Status Message */}
          {testStatus !== 'idle' && (
            <div
              className={`p-3 rounded-lg border text-[11px] flex items-start gap-2 ${
                testStatus === 'success'
                  ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-300'
                  : testStatus === 'error'
                  ? 'bg-rose-950/30 border-rose-800/60 text-rose-300'
                  : 'bg-neutral-900 border-neutral-800 text-neutral-300'
              }`}
            >
              {testStatus === 'success' && <CheckIcon className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />}
              {testStatus === 'error' && <AlertTriangleIcon className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />}
              {testStatus === 'testing' && <RefreshCwIcon className="w-3.5 h-3.5 text-neutral-400 shrink-0 mt-0.5 animate-spin" />}
              <div className="flex-1">
                <div className="font-medium flex items-center justify-between">
                  <span>{testStatus === 'success' ? 'Connected' : testStatus === 'error' ? 'Connection Failed' : 'Pinging Endpoint...'}</span>
                  {testPing !== null && <span className="font-mono text-[10px]">{testPing} ms</span>}
                </div>
                {testMessage && <p className="mt-0.5 text-neutral-400 font-mono text-[10px]">{testMessage}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-neutral-800 bg-[#0f1116]">
          <button
            type="button"
            onClick={handleReset}
            className="text-[11px] text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            Reset Default
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleTest}
              disabled={testStatus === 'testing'}
              className="px-3 py-1.5 rounded-md border border-neutral-700 bg-neutral-800/60 hover:bg-neutral-700/60 text-neutral-200 text-xs font-medium flex items-center gap-1.5 transition-colors"
            >
              <RefreshCwIcon className={`w-3 h-3 ${testStatus === 'testing' ? 'animate-spin' : ''}`} />
              <span>Test Ping</span>
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-3.5 py-1.5 rounded-md bg-neutral-100 hover:bg-white text-neutral-900 font-medium text-xs transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
