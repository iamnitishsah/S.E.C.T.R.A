import React, { useState } from 'react';
import type { AskResponse, Passage } from '../types/api';
import { submitQuestion } from '../services/api';
import { ArrowRightIcon, ExternalLinkIcon, CopyIcon, CheckIcon } from '../components/common/Icons';

const ROUTE_STYLE: Record<string, { label: string; color: string }> = {
  sql: { label: 'Database', color: 'bg-sql' },
  text: { label: 'Filing text', color: 'bg-text' },
  both: { label: 'Database + filing text', color: 'bg-both' },
  none: { label: 'Declined', color: 'bg-danger' },
};

const PRESETS: { group: string; queries: string[] }[] = [
  {
    group: 'Numbers',
    queries: [
      'Which companies grew revenue by more than 20% in fiscal 2025?',
      'Which semiconductor company had the highest net income in fiscal 2025?',
    ],
  },
  {
    group: 'Filing text',
    queries: [
      "What export restrictions affect NVIDIA's sales to China?",
      'What cybersecurity governance structure does Microsoft describe in Item 1C?',
    ],
  },
  {
    group: 'Both',
    queries: [
      'Which healthcare company grew revenue fastest in fiscal 2025, and what drove that growth?',
      "How fast did Nvidia's revenue grow in fiscal 2025, and what drove it?",
    ],
  },
  {
    group: 'Should decline',
    queries: ["What is Tesla's battery supply strategy?", "What was Apple's stock price on June 1 2024?"],
  },
];

const PassageItem: React.FC<{ p: Passage; active: boolean }> = ({ p, active }) => {
  const [open, setOpen] = useState(false);
  const expanded = open || active;
  return (
    <li
      id={`passage-${p.n}`}
      className={`py-5 border-b border-rule scroll-mt-24 transition-colors ${active ? 'bg-accent-soft/40 -mx-4 px-4 rounded-lg' : ''}`}
    >
      <div className="flex gap-4">
        <span
          className={`shrink-0 w-6 h-6 rounded-full grid place-items-center font-mono text-xs ${
            p.cited ? 'bg-ink text-bg' : 'border border-rule-strong text-muted'
          }`}
        >
          {p.n}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="text-sm font-medium text-ink">{p.header}</p>
            <div className="flex items-center gap-3 text-xs text-muted">
              {!p.cited && <span className="text-faint">not cited</span>}
              <span className="font-mono tabular">score {p.score.toFixed(3)}</span>
              {p.url && (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-ink-2 hover:text-ink underline-offset-2 hover:underline"
                >
                  EDGAR
                  <ExternalLinkIcon className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
          <p className={`mt-2 text-sm leading-relaxed text-ink-2 ${expanded ? '' : 'line-clamp-3'}`}>{p.text}</p>
          <div className="mt-2 flex items-center gap-4 text-xs text-faint">
            <button onClick={() => setOpen(!open)} className="text-muted hover:text-ink">
              {expanded ? 'Show less' : 'Show more'}
            </button>
            <span className="font-mono truncate">{p.chunk_id}</span>
          </div>
        </div>
      </div>
    </li>
  );
};

export const DemoPage: React.FC = () => {
  const [question, setQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<'answer' | 'sql' | null>(null);
  const [activePassage, setActivePassage] = useState<number | null>(null);

  const handleAsk = async (queryToAsk?: string) => {
    const q = (queryToAsk || question).trim();
    if (!q || loading) return;
    if (queryToAsk) setQuestion(queryToAsk);

    setLoading(true);
    setError(null);
    setActivePassage(null);
    try {
      setResponse(await submitQuestion(q));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'The question could not be processed');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, what: 'answer' | 'sql') => {
    navigator.clipboard.writeText(text);
    setCopied(what);
    setTimeout(() => setCopied(null), 1800);
  };

  const scrollTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });

  const renderCitations = (text: string) =>
    text.split(/(\[T\]|\[\d+\])/g).map((part, idx) => {
      if (part === '[T]') {
        return (
          <button
            key={idx}
            onClick={() => scrollTo('evidence-table')}
            className="relative -top-px mx-0.5 px-1 rounded font-mono text-[11px] font-medium text-sql bg-accent-soft hover:brightness-95 align-middle"
            title="Database result"
          >
            T
          </button>
        );
      }
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const n = parseInt(match[1], 10);
        return (
          <button
            key={idx}
            onClick={() => {
              setActivePassage(n);
              scrollTo(`passage-${n}`);
            }}
            className="relative -top-px mx-0.5 min-w-[1.25rem] px-1 rounded font-mono text-[11px] font-medium text-text bg-sunken hover:bg-rule align-middle"
            title={`Passage ${n}`}
          >
            {n}
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });

  const route = response ? ROUTE_STYLE[response.answered ? response.route : 'none'] ?? ROUTE_STYLE.none : null;
  const warnings = response?.warnings ?? {};
  const hasWarnings =
    !!warnings.uncited_sentences?.length || !!warnings.unsupported_numbers?.length || !!warnings.truncated;

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="font-serif text-[2.25rem] sm:text-[2.75rem] leading-[1.1] tracking-[-0.01em]">
        Ask the filings
      </h1>
      <p className="mt-3 text-[15px] text-ink-2">
        Questions about figures, narrative, or both, across 20 companies and 80 annual reports.
      </p>

      {/* Question box */}
      <form
        className="mt-8 bg-surface border border-rule-strong rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] focus-within:border-ink/40 transition-colors"
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleAsk();
            }
          }}
          rows={2}
          placeholder="e.g. How fast did Nvidia’s revenue grow in fiscal 2025, and what drove it?"
          className="block w-full resize-none bg-transparent px-4 pt-4 pb-2 text-[15px] leading-relaxed placeholder:text-faint focus:outline-none"
        />
        <div className="flex items-center justify-between px-3 pb-3">
          <span className="pl-1 text-xs text-faint hidden sm:inline">Enter to ask · Shift+Enter for a new line</span>
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="ml-auto inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-ink text-bg text-sm font-medium disabled:opacity-30 transition-opacity"
          >
            {loading ? 'Researching…' : 'Ask'}
            {!loading && <ArrowRightIcon className="w-3.5 h-3.5" />}
          </button>
        </div>
      </form>

      {/* Examples */}
      {!response && !loading && (
        <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-x-10 gap-y-6">
          {PRESETS.map((g) => (
            <div key={g.group}>
              <p className="text-xs font-medium text-muted uppercase tracking-[0.1em] mb-2">{g.group}</p>
              <ul className="space-y-1">
                {g.queries.map((q) => (
                  <li key={q}>
                    <button
                      onClick={() => handleAsk(q)}
                      className="text-left text-sm text-ink-2 hover:text-ink leading-snug py-1 hover:underline underline-offset-4 decoration-rule-strong"
                    >
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="mt-12" aria-live="polite">
          <p className="text-sm text-muted">Routing the question, querying the database and searching filings…</p>
          <div className="mt-5 space-y-3">
            {[100, 92, 96, 60].map((w, i) => (
              <div key={i} className="h-3.5 rounded bg-rule animate-pulse" style={{ width: `${w}%` }} />
            ))}
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="mt-8 rounded-lg bg-danger-soft text-danger px-4 py-3 text-sm">
          <p className="font-medium">Something went wrong</p>
          <p className="mt-0.5 text-xs opacity-80">{error}</p>
        </div>
      )}

      {/* Answer */}
      {response && !loading && route && (
        <article className="mt-12">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
            <span className="inline-flex items-center gap-1.5 text-ink-2 font-medium">
              <span className={`w-1.5 h-1.5 rounded-full ${route.color}`} />
              {route.label}
            </span>
            {response.tickers?.length > 0 && <span className="font-mono">{response.tickers.join(', ')}</span>}
            {response.fiscal_years?.length > 0 && (
              <span className="font-mono">FY {response.fiscal_years.join(', ')}</span>
            )}
            <span className="font-mono tabular">{(response.latency_ms / 1000).toFixed(1)} s</span>
            {response.model && <span className="font-mono hidden sm:inline">{response.model}</span>}
          </div>

          <div className="mt-4 pt-5 border-t border-rule">
            {response.answered ? (
              <div className="font-serif text-[1.2rem] leading-[1.7] text-ink whitespace-pre-wrap">
                {renderCitations(response.answer)}
              </div>
            ) : (
              <div>
                <p className="font-serif text-[1.2rem] leading-[1.7] text-ink">
                  {response.answer || 'Not found in the indexed filings.'}
                </p>
                {response.reason && <p className="mt-2 text-sm text-muted">Reason: {response.reason}</p>}
              </div>
            )}

            {hasWarnings && (
              <div className="mt-5 rounded-lg bg-warn-soft text-warn px-4 py-3 text-sm space-y-1">
                <p className="font-medium">Checks flagged part of this answer</p>
                {!!warnings.uncited_sentences?.length && (
                  <p className="text-xs">Without a citation: {warnings.uncited_sentences.join(' · ')}</p>
                )}
                {!!warnings.unsupported_numbers?.length && (
                  <p className="text-xs">Numbers not in the evidence: {warnings.unsupported_numbers.join(', ')}</p>
                )}
                {warnings.truncated && <p className="text-xs">The answer hit the token limit and may be cut off.</p>}
              </div>
            )}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              {response.steps?.length > 0 ? (
                <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted font-mono">
                  {response.steps.map((s, i) => (
                    <li key={i} className="flex items-center gap-2">
                      {i > 0 && <span className="text-faint">→</span>}
                      {s}
                    </li>
                  ))}
                </ol>
              ) : (
                <span />
              )}
              <button
                onClick={() => handleCopy(response.answer, 'answer')}
                className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink"
              >
                {copied === 'answer' ? <CheckIcon className="w-3.5 h-3.5" /> : <CopyIcon className="w-3.5 h-3.5" />}
                {copied === 'answer' ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Database evidence */}
          {response.table && (
            <section id="evidence-table" className="mt-14 scroll-mt-24">
              <div className="flex items-baseline justify-between gap-4 pb-3 border-b border-rule-strong">
                <h2 className="text-sm font-semibold">
                  Database result <span className="font-mono font-normal text-muted">[T]</span>
                </h2>
                <button
                  onClick={() => handleCopy(response.table?.sql || '', 'sql')}
                  className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink"
                >
                  {copied === 'sql' ? <CheckIcon className="w-3.5 h-3.5" /> : <CopyIcon className="w-3.5 h-3.5" />}
                  {copied === 'sql' ? 'Copied' : 'Copy SQL'}
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-muted border-b border-rule">
                      {response.table.columns.map((col, i) => (
                        <th key={i} className="font-medium font-mono py-2.5 pr-6 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {response.table.rows.map((row, r) => (
                      <tr key={r} className="border-b border-rule">
                        {row.map((cell, c) => (
                          <td
                            key={c}
                            className={`py-2.5 pr-6 whitespace-nowrap font-mono text-[13px] tabular ${
                              typeof cell === 'number' ? 'text-ink' : 'text-ink-2'
                            }`}
                          >
                            {cell === null ? <span className="text-faint">—</span> : String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <details className="mt-4 group">
                <summary className="text-xs text-muted hover:text-ink cursor-pointer select-none list-none">
                  <span className="group-open:hidden">Show SQL</span>
                  <span className="hidden group-open:inline">Hide SQL</span>
                </summary>
                <pre className="mt-3 p-4 rounded-lg bg-sunken text-[12.5px] font-mono leading-relaxed text-ink-2 whitespace-pre-wrap overflow-x-auto">
                  {response.table.sql}
                </pre>
              </details>

              {response.table.source_filings?.length > 0 && (
                <p className="mt-3 text-xs text-muted">
                  Source filings:{' '}
                  <span className="font-mono text-ink-2">{response.table.source_filings.join(', ')}</span>
                </p>
              )}
            </section>
          )}

          {/* Passage evidence */}
          {response.passages?.length > 0 && (
            <section className="mt-14">
              <div className="flex items-baseline justify-between gap-4 pb-1 border-b border-rule-strong">
                <h2 className="text-sm font-semibold pb-2">Filing passages</h2>
                <span className="text-xs text-muted">
                  {response.passages.filter((p) => p.cited).length} of {response.passages.length} cited
                </span>
              </div>
              <ol>
                {response.passages.map((p) => (
                  <PassageItem key={p.n} p={p} active={activePassage === p.n} />
                ))}
              </ol>
            </section>
          )}

          <button
            onClick={() => {
              setResponse(null);
              setQuestion('');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="mt-10 text-sm text-muted hover:text-ink"
          >
            ← Ask another question
          </button>
        </article>
      )}
    </div>
  );
};
