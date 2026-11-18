import React, { useState, useEffect } from 'react';
import { getStoredApiKey, saveStoredApiKey, resetStoredApiKey, checkHealth, API_BASE_URL } from '../../services/api';
import { XIcon } from '../common/Icons';

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

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTestStatus('testing');
    setTestMessage('');
    setTestPing(null);
    try {
      saveStoredApiKey(apiKey);
      const { data, pingMs } = await checkHealth();
      setTestStatus('success');
      setTestPing(pingMs);
      setTestMessage(`${data.companies} companies loaded · ${data.llm || 'model configured'}`);
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
    setApiKey(resetStoredApiKey());
    setTestStatus('idle');
    setTestMessage('');
    onConfigChanged();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px] p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-surface border border-rule rounded-xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.25)]"
      >
        <div className="flex items-start justify-between px-6 pt-5">
          <div>
            <h3 id="settings-title" className="text-base font-semibold">API access</h3>
            <p className="mt-1 text-sm text-muted">The key is sent as the X-API-Key header with every question.</p>
          </div>
          <button onClick={onClose} className="p-1 -mr-1 rounded text-muted hover:text-ink" aria-label="Close">
            <XIcon className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          <div>
            <div className="text-xs font-medium text-muted mb-1.5">Endpoint</div>
            <div className="font-mono text-xs text-ink-2 truncate select-all">{API_BASE_URL}</div>
          </div>

          <label className="block">
            <span className="text-xs font-medium text-muted">API key</span>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestStatus('idle');
              }}
              spellCheck={false}
              autoComplete="off"
              className="mt-1.5 w-full bg-bg border border-rule-strong rounded-lg px-3 py-2 font-mono text-sm text-ink focus:outline-none focus:border-accent transition-colors"
            />
          </label>

          {testStatus !== 'idle' && (
            <div
              className={`rounded-lg px-3 py-2.5 text-sm ${
                testStatus === 'success'
                  ? 'bg-accent-soft text-accent'
                  : testStatus === 'error'
                  ? 'bg-danger-soft text-danger'
                  : 'bg-sunken text-muted'
              }`}
            >
              <div className="flex items-center justify-between font-medium">
                <span>
                  {testStatus === 'success' ? 'Connected' : testStatus === 'error' ? 'Could not connect' : 'Testing…'}
                </span>
                {testPing !== null && <span className="font-mono text-xs tabular">{testPing} ms</span>}
              </div>
              {testMessage && <p className="mt-0.5 text-xs opacity-80 break-words">{testMessage}</p>}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-rule">
          <button type="button" onClick={handleReset} className="text-sm text-muted hover:text-ink">
            Reset to default
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleTest}
              disabled={testStatus === 'testing'}
              className="px-3.5 py-1.5 rounded-md border border-rule-strong text-sm text-ink-2 hover:bg-bg disabled:opacity-50"
            >
              Test
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-3.5 py-1.5 rounded-md bg-ink text-bg text-sm font-medium hover:opacity-90"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
