import React, { useState } from 'react';
import type { AskResponse, Passage } from '../types/api';
import { submitQuestion } from '../services/api';
import {
  TerminalIcon,
  SearchIcon,
  DatabaseIcon,
  FileTextIcon,
  LayersIcon,
  ShieldCheckIcon,
  AlertTriangleIcon,
  ExternalLinkIcon,
  CopyIcon,
  CheckIcon,
  RefreshCwIcon,
  ClockIcon,
  XIcon
} from '../components/common/Icons';

interface QueryPreset {
  type: 'numeric' | 'narrative' | 'hybrid' | 'refusal';
  typeLabel: string;
  query: string;
}

const PRESETS: QueryPreset[] = [
  {
    type: 'hybrid',
    typeLabel: 'Hybrid',
    query: 'Which healthcare company grew revenue fastest in fiscal 2025, and what drove that growth?',
  },
  {
    type: 'numeric',
    typeLabel: 'SQL Metric',
    query: 'Which companies grew revenue by more than 20% in fiscal 2025?',
  },
  {
    type: 'numeric',
    typeLabel: 'SQL Metric',
    query: 'Which semiconductor company had the highest net income in fiscal 2025?',
  },
  {
    type: 'narrative',
    typeLabel: '10-K Filing',
    query: "What export restrictions affect NVIDIA's sales to China?",
  },
  {
    type: 'narrative',
    typeLabel: '10-K Filing',
    query: 'What cybersecurity governance structure does Microsoft describe in Item 1C?',
  },
  {
    type: 'hybrid',
    typeLabel: 'Hybrid',
    query: "How fast did Nvidia's revenue grow in fiscal 2025, and what drove it?",
  },
  {
    type: 'refusal',
    typeLabel: 'Refusal Test',
    query: "What is Tesla's battery supply strategy?",
  },
  {
    type: 'refusal',
    typeLabel: 'Refusal Test',
    query: "What was Apple's stock price on June 1 2024?",
  },
];

export const DemoPage: React.FC = () => {
  const [question, setQuestion] = useState<string>(
    'Which healthcare company grew revenue fastest in fiscal 2025, and what drove that growth?'
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [evidenceTab, setEvidenceTab] = useState<'all' | 'table' | 'passages'>('all');
  const [copiedAnswer, setCopiedAnswer] = useState<boolean>(false);
  const [copiedSql, setCopiedSql] = useState<boolean>(false);
  const [activePassage, setActivePassage] = useState<number | null>(null);

  const handleAsk = async (queryToAsk?: string) => {
    const q = (queryToAsk || question).trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setActivePassage(null);

    try {
      const data = await submitQuestion(q);
      setResponse(data);
      if (queryToAsk) {
        setQuestion(queryToAsk);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query S.E.C.T.R.A API');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, isSql: boolean = false) => {
    navigator.clipboard.writeText(text);
    if (isSql) {
      setCopiedSql(true);
      setTimeout(() => setCopiedSql(false), 2000);
    } else {
      setCopiedAnswer(true);
      setTimeout(() => setCopiedAnswer(false), 2000);
    }
  };

  // Render citation tokens [T] and [n] as clean interactive buttons
  const renderCitations = (text: string) => {
    const parts = text.split(/(\[T\]|\[\d+\])/g);
    return parts.map((part, idx) => {
      if (part === '[T]') {
        return (
          <button
            key={idx}
            onClick={() => {
              setEvidenceTab('table');
              const el = document.getElementById('evidence-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 hover:bg-emerald-900/60 transition-colors cursor-pointer"
            title="Inspect executed SQL result table"
          >
            [T]
          </button>
        );
      }
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const passageNum = parseInt(match[1], 10);
        return (
          <button
            key={idx}
            onClick={() => {
              setEvidenceTab('passages');
              setActivePassage(passageNum);
              const el = document.getElementById(`passage-${passageNum}`);
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-mono font-medium bg-sky-950/80 text-sky-300 border border-sky-800/80 hover:bg-sky-900/60 transition-colors cursor-pointer"
            title={`Inspect 10-K source passage #${passageNum}`}
          >
            [{passageNum}]
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="space-y-8 pb-20">
      {/* Header */}
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
          <TerminalIcon className="w-5 h-5 text-neutral-300" />
          <span>SEC Research Terminal</span>
        </h2>
        <p className="text-xs text-neutral-400">
          Ask questions across 80 annual 10-K reports and normalized XBRL metrics. Every answer is grounded in database rows or cited text.
        </p>
      </div>

      {/* Query Bar */}
      <div className="space-y-3">
        <div className="relative flex items-center bg-[#101318] border border-neutral-800 rounded-xl overflow-hidden focus-within:border-neutral-600 focus-within:ring-1 focus-within:ring-neutral-600 transition-all">
          <div className="pl-4 pr-2 text-neutral-500">
            <SearchIcon className="w-4 h-4 text-neutral-400" />
          </div>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !loading) {
                handleAsk();
              }
            }}
            placeholder="Ask a financial or narrative question..."
            className="w-full bg-transparent py-3.5 pr-2 text-white placeholder-neutral-500 text-sm font-sans focus:outline-hidden"
          />
          {question && (
            <button
              onClick={() => setQuestion('')}
              className="p-1 text-neutral-500 hover:text-neutral-300 rounded mr-1"
            >
              <XIcon className="w-4 h-4" />
            </button>
          )}
          <div className="pr-2">
            <button
              onClick={() => handleAsk()}
              disabled={loading || !question.trim()}
              className="px-4 py-2 rounded-lg bg-neutral-100 hover:bg-white disabled:bg-neutral-800 disabled:text-neutral-500 text-neutral-900 font-medium text-xs font-mono flex items-center gap-2 transition-all cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCwIcon className="w-3.5 h-3.5 animate-spin" />
                  <span>Researching...</span>
                </>
              ) : (
                <span>Submit Query</span>
              )}
            </button>
          </div>
        </div>

        {/* Example Presets (clean, organized list) */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-mono text-neutral-500 uppercase tracking-wider block">
            Example Research Inquiries:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuestion(p.query);
                  handleAsk(p.query);
                }}
                disabled={loading}
                className="px-2.5 py-1 rounded bg-[#101318] hover:bg-neutral-800 border border-neutral-800 hover:border-neutral-700 text-xs text-neutral-300 font-sans text-left transition-colors flex items-center gap-1.5"
              >
                <span className="font-mono text-[10px] text-neutral-500 uppercase">
                  {p.typeLabel}
                </span>
                <span className="text-neutral-600">•</span>
                <span className="truncate max-w-xs md:max-w-md">{p.query}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-[#140e10] border border-rose-900/60 text-rose-300 text-xs flex items-start gap-3">
          <AlertTriangleIcon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1 font-mono">
            <p className="font-semibold text-rose-200">Execution Error</p>
            <p className="text-neutral-300 text-xs font-sans">{error}</p>
          </div>
        </div>
      )}

      {/* Response Panel */}
      {response && (
        <div className="space-y-6">
          {/* Metadata & Step Trace */}
          <div className="border border-neutral-800 rounded-xl bg-[#101318] p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                {/* Route Badge */}
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-medium border border-neutral-800 bg-neutral-900 text-neutral-200">
                  {response.route === 'sql' && <DatabaseIcon className="w-3.5 h-3.5 text-emerald-400" />}
                  {response.route === 'text' && <FileTextIcon className="w-3.5 h-3.5 text-sky-400" />}
                  {response.route === 'both' && <LayersIcon className="w-3.5 h-3.5 text-amber-400" />}
                  {(!response.answered || response.route === 'none') && <ShieldCheckIcon className="w-3.5 h-3.5 text-rose-400" />}
                  <span className="uppercase">
                    {response.answered ? `Route: ${response.route}` : 'Refusal (Out of Scope)'}
                  </span>
                </span>

                {/* Ticker / Year Scoping */}
                {response.tickers && response.tickers.length > 0 && (
                  <span className="text-neutral-400 font-mono text-xs">
                    Target: <span className="text-white font-semibold">{response.tickers.join(', ')}</span>
                  </span>
                )}
                {response.fiscal_years && response.fiscal_years.length > 0 && (
                  <span className="text-neutral-400 font-mono text-xs">
                    FY: <span className="text-neutral-200">{response.fiscal_years.join(', ')}</span>
                  </span>
                )}
              </div>

              {/* Execution Latency & Model */}
              <div className="flex items-center gap-3 text-[11px] font-mono text-neutral-400">
                <span className="flex items-center gap-1">
                  <ClockIcon className="w-3 h-3 text-neutral-500" />
                  <span>{response.latency_ms}ms</span>
                </span>
                {response.model && (
                  <span className="hidden sm:inline border-l border-neutral-800 pl-3">
                    {response.model}
                  </span>
                )}
              </div>
            </div>

            {/* Orchestration Trace */}
            {response.steps && response.steps.length > 0 && (
              <div className="pt-2 border-t border-neutral-800/80 flex flex-wrap items-center gap-1.5 text-[11px] font-mono text-neutral-400">
                <span className="text-neutral-500 mr-1">Trace:</span>
                {response.steps.map((st, i) => (
                  <React.Fragment key={i}>
                    <span className="px-2 py-0.5 rounded bg-[#0c0e12] border border-neutral-800 text-neutral-300">
                      {st}
                    </span>
                    {i < response.steps.length - 1 && <span className="text-neutral-600">→</span>}
                  </React.Fragment>
                ))}
              </div>
            )}
          </div>

          {/* Synthesized Answer */}
          <div className="border border-neutral-800 rounded-xl bg-[#101318] p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-neutral-800/80 pb-3">
              <span className="text-xs font-mono font-medium uppercase tracking-wider text-neutral-400">
                Audited Research Answer
              </span>
              <button
                onClick={() => handleCopy(response.answer)}
                className="text-xs text-neutral-400 hover:text-neutral-200 flex items-center gap-1.5 p-1 rounded hover:bg-neutral-800 transition-colors"
                title="Copy Answer"
              >
                {copiedAnswer ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
                <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            <div className="text-neutral-100 text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {response.answered ? (
                renderCitations(response.answer)
              ) : (
                <div className="space-y-2">
                  <p className="text-neutral-200 font-medium">
                    {response.answer || 'Not found in the indexed filings.'}
                  </p>
                  {response.reason && (
                    <p className="text-xs text-neutral-400 font-mono">
                      Refusal Reason: <span className="text-neutral-300">{response.reason}</span>
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Verification Warnings (if any) */}
            {response.warnings && Object.keys(response.warnings).length > 0 && (
              <div className="mt-4 p-3 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-amber-400 text-xs font-mono">
                  <AlertTriangleIcon className="w-3.5 h-3.5" />
                  <span>Auditor Safeguard Notice</span>
                </div>
                {response.warnings.uncited_sentences && (
                  <p className="text-[11px] text-neutral-400">
                    • Uncited sentence detected: {response.warnings.uncited_sentences.join('; ')}
                  </p>
                )}
                {response.warnings.unsupported_numbers && (
                  <p className="text-[11px] text-neutral-400">
                    • Number not found in database rows: {response.warnings.unsupported_numbers.join(', ')}
                  </p>
                )}
                {response.warnings.truncated && (
                  <p className="text-[11px] text-amber-400">
                    • Generation hit token limit.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Evidence Inspector Tabs */}
          <div id="evidence-section" className="space-y-4">
            <div className="flex items-center gap-2 border-b border-neutral-800 pb-2">
              <button
                onClick={() => setEvidenceTab('all')}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  evidenceTab === 'all'
                    ? 'bg-neutral-800 text-white'
                    : 'text-neutral-400 hover:text-neutral-200'
                }`}
              >
                All Evidence
              </button>
              {response.table && (
                <button
                  onClick={() => setEvidenceTab('table')}
                  className={`px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1.5 transition-colors ${
                    evidenceTab === 'table'
                      ? 'bg-neutral-800 text-white'
                      : 'text-neutral-400 hover:text-neutral-200'
                  }`}
                >
                  <DatabaseIcon className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Database Result [T]</span>
                </button>
              )}
              {response.passages && response.passages.length > 0 && (
                <button
                  onClick={() => setEvidenceTab('passages')}
                  className={`px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1.5 transition-colors ${
                    evidenceTab === 'passages'
                      ? 'bg-neutral-800 text-white'
                      : 'text-neutral-400 hover:text-neutral-200'
                  }`}
                >
                  <FileTextIcon className="w-3.5 h-3.5 text-sky-400" />
                  <span>10-K Passages ({response.passages.length})</span>
                </button>
              )}
            </div>

            {/* Tab Content: SQL Result Table */}
            {(evidenceTab === 'all' || evidenceTab === 'table') && response.table && (
              <div className="border border-neutral-800 rounded-xl bg-[#101318] p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-emerald-400">
                      Citation [T]
                    </span>
                    <span className="text-neutral-600">|</span>
                    <span className="text-xs text-neutral-300 font-medium">
                      Executed SQL Result ({response.table.rows.length} rows)
                    </span>
                  </div>
                  <button
                    onClick={() => handleCopy(response.table?.sql || '', true)}
                    className="text-xs text-neutral-400 hover:text-neutral-200 flex items-center gap-1 p-1 rounded hover:bg-neutral-800 transition-colors"
                  >
                    {copiedSql ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
                    <span>{copiedSql ? 'Copied' : 'Copy SQL'}</span>
                  </button>
                </div>

                {/* SQL Query Snippet */}
                <div className="p-3 rounded-lg bg-[#0c0e12] border border-neutral-800 overflow-x-auto">
                  <pre className="text-xs font-mono text-neutral-300 whitespace-pre-wrap leading-relaxed">
                    {response.table.sql}
                  </pre>
                </div>

                {/* Data Table */}
                <div className="overflow-x-auto rounded-lg border border-neutral-800">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-[#0c0e12] border-b border-neutral-800 text-neutral-400 uppercase text-[10px]">
                      <tr>
                        {response.table.columns.map((col, i) => (
                          <th key={i} className="px-3 py-2.5 font-medium">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/60 bg-[#101318]">
                      {response.table.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-neutral-800/40 transition-colors">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="px-3 py-2 text-neutral-200 whitespace-nowrap">
                              {cell === null ? (
                                <span className="text-neutral-600 italic">NULL</span>
                              ) : typeof cell === 'number' ? (
                                <span className="text-emerald-400 font-semibold">{cell}</span>
                              ) : (
                                cell.toString()
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Source Accession */}
                {response.table.source_filings && response.table.source_filings.length > 0 && (
                  <div className="text-[11px] font-mono text-neutral-500 flex items-center gap-2">
                    <span>Source Accession:</span>
                    {response.table.source_filings.map((acc, aIdx) => (
                      <span key={aIdx} className="text-neutral-300 bg-[#0c0e12] px-2 py-0.5 rounded border border-neutral-800">
                        {acc}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab Content: Filing Passages */}
            {(evidenceTab === 'all' || evidenceTab === 'passages') && response.passages && response.passages.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-neutral-500 px-1">
                  <span>Candidate 10-K Passages ({response.passages.length} Scored by Cross-Encoder)</span>
                </div>

                <div className="space-y-3">
                  {response.passages.map((p: Passage) => {
                    const isSelected = activePassage === p.n;
                    return (
                      <div
                        key={p.n}
                        id={`passage-${p.n}`}
                        className={`border rounded-xl p-4 transition-all bg-[#101318] space-y-2.5 ${
                          isSelected ? 'border-sky-500 ring-1 ring-sky-500/40' : 'border-neutral-800'
                        }`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-neutral-900 border border-neutral-800 text-sky-400">
                              [{p.n}]
                            </span>
                            {p.cited && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 border border-emerald-800/80 text-emerald-400">
                                Cited
                              </span>
                            )}
                            <span className="text-xs font-mono font-medium text-neutral-200">
                              {p.header}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-xs font-mono text-neutral-400">
                            <span>Score: <strong className="text-neutral-200">{p.score}</strong></span>
                            {p.url && (
                              <a
                                href={p.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 hover:underline"
                              >
                                <span>SEC EDGAR</span>
                                <ExternalLinkIcon className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        </div>

                        {/* Text */}
                        <div className="p-3 rounded-lg bg-[#0c0e12] border border-neutral-800/80 text-xs text-neutral-300 leading-relaxed font-sans">
                          {p.text}
                        </div>

                        {/* Metadata Footer */}
                        <div className="flex items-center gap-3 text-[10px] font-mono text-neutral-500">
                          <span>Chunk ID: {p.chunk_id}</span>
                          {p.item_code && <span>Item: {p.item_code}</span>}
                          {p.fiscal_year && <span>FY: {p.fiscal_year}</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
