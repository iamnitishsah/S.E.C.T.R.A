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
  SparklesIcon,
  ClockIcon,
  CpuIcon,
  HashIcon,
  XIcon
} from '../components/common/Icons';

interface PresetQuery {
  category: 'numeric' | 'narrative' | 'hybrid' | 'refusal';
  label: string;
  question: string;
}

const PRESET_QUERIES: PresetQuery[] = [
  {
    category: 'numeric',
    label: 'Revenue Growth > 20%',
    question: 'Which companies grew revenue by more than 20% in fiscal 2025?',
  },
  {
    category: 'numeric',
    label: 'Top Semis Net Income',
    question: 'Which semiconductor company had the highest net income in fiscal 2025?',
  },
  {
    category: 'narrative',
    label: 'NVIDIA China Export Rules',
    question: "What export restrictions affect NVIDIA's sales to China?",
  },
  {
    category: 'narrative',
    label: 'MSFT Item 1C Cyber',
    question: 'What cybersecurity governance structure does Microsoft describe in Item 1C?',
  },
  {
    category: 'hybrid',
    label: 'Fastest Healthcare & Drivers',
    question: 'Which healthcare company grew revenue fastest in fiscal 2025, and what drove that growth?',
  },
  {
    category: 'hybrid',
    label: 'NVIDIA FY2025 Growth & Drivers',
    question: "How fast did Nvidia's revenue grow in fiscal 2025, and what drove it?",
  },
  {
    category: 'refusal',
    label: 'Unindexed Company (Tesla)',
    question: "What is Tesla's battery supply strategy?",
  },
  {
    category: 'refusal',
    label: 'Stock Price (Out of Scope)',
    question: "What was Apple's stock price on June 1 2024?",
  },
];

export const DemoPage: React.FC = () => {
  const [question, setQuestion] = useState<string>('Which healthcare company grew revenue fastest in fiscal 2025, and what drove that growth?');
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'evidence' | 'table' | 'passages' | 'trace'>('evidence');
  const [copiedAnswer, setCopiedAnswer] = useState<boolean>(false);
  const [copiedSql, setCopiedSql] = useState<boolean>(false);
  const [highlightedPassage, setHighlightedPassage] = useState<number | null>(null);
  const [highlightedTable, setHighlightedTable] = useState<boolean>(false);

  const handleAsk = async (queryToAsk?: string) => {
    const q = (queryToAsk || question).trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setHighlightedPassage(null);
    setHighlightedTable(false);

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

  const renderCitationText = (text: string) => {
    // Regex splits by [T] or [1], [2], etc.
    const parts = text.split(/(\[T\]|\[\d+\])/g);
    return parts.map((part, idx) => {
      if (part === '[T]') {
        return (
          <button
            key={idx}
            onClick={() => {
              setActiveTab('table');
              setHighlightedTable(true);
              setTimeout(() => setHighlightedTable(false), 3000);
            }}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[11px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-600/60 hover:bg-emerald-900 transition-colors"
            title="Click to inspect SQL result table"
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
              setActiveTab('passages');
              setHighlightedPassage(passageNum);
              setTimeout(() => setHighlightedPassage(null), 4000);
            }}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[11px] font-mono font-bold bg-sky-950/80 text-sky-300 border border-sky-600/60 hover:bg-sky-900 transition-colors"
            title={`Click to inspect passage #${passageNum}`}
          >
            [{passageNum}]
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  const getRouteBadge = (route: string, answered: boolean) => {
    if (!answered || route === 'none') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-rose-950/80 text-rose-300 border border-rose-800">
          <ShieldCheckIcon className="w-3.5 h-3.5 text-rose-400" />
          <span>REFUSED / OUT OF CORPUS</span>
        </span>
      );
    }
    if (route === 'sql') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
          <DatabaseIcon className="w-3.5 h-3.5 text-emerald-400" />
          <span>ROUTE: SQL ANALYST</span>
        </span>
      );
    }
    if (route === 'text') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-sky-950/80 text-sky-300 border border-sky-800">
          <FileTextIcon className="w-3.5 h-3.5 text-sky-400" />
          <span>ROUTE: 10-K RAG RETRIEVAL</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-amber-950/80 text-amber-300 border border-amber-800">
        <LayersIcon className="w-3.5 h-3.5 text-amber-400" />
        <span>ROUTE: HYBRID (SQL + RAG)</span>
      </span>
    );
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Control Bar: Title & Preset Buttons */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TerminalIcon className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-slate-100 font-mono">SEC Research Terminal</h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Targeting AWS EC2 API
          </span>
        </div>

        {/* Preset Query Chips */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
            <SparklesIcon className="w-3 h-3 text-emerald-400" />
            <span>Preset Domain Benchmarks:</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {PRESET_QUERIES.map((p, idx) => {
              const categoryColors = {
                numeric: 'hover:border-emerald-500/70 text-slate-300 hover:text-emerald-300 bg-slate-900/80',
                narrative: 'hover:border-sky-500/70 text-slate-300 hover:text-sky-300 bg-slate-900/80',
                hybrid: 'hover:border-amber-500/70 text-slate-300 hover:text-amber-300 bg-slate-900/80',
                refusal: 'hover:border-rose-500/70 text-slate-300 hover:text-rose-300 bg-slate-900/80',
              };
              return (
                <button
                  key={idx}
                  onClick={() => {
                    setQuestion(p.question);
                    handleAsk(p.question);
                  }}
                  disabled={loading}
                  className={`text-xs px-2.5 py-1 rounded-lg border border-slate-800 transition-all font-mono text-left flex items-center gap-1.5 ${categoryColors[p.category]}`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                  <span>{p.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Query Bar */}
      <div className="relative">
        <div className="relative flex items-center bg-slate-900 border border-slate-800 rounded-xl overflow-hidden focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500 transition-all shadow-xl">
          <div className="pl-4 pr-2 text-slate-500">
            <SearchIcon className="w-5 h-5 text-emerald-400" />
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
            placeholder="Ask anything across 80 SEC 10-K filings or financial metrics..."
            className="w-full bg-transparent py-3.5 pr-2 text-slate-100 placeholder-slate-500 text-sm font-sans focus:outline-hidden"
          />
          {question && (
            <button
              onClick={() => setQuestion('')}
              className="p-1.5 text-slate-500 hover:text-slate-300 rounded mr-1"
            >
              <XIcon className="w-4 h-4" />
            </button>
          )}
          <div className="pr-2">
            <button
              onClick={() => handleAsk()}
              disabled={loading || !question.trim()}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-xs font-mono flex items-center gap-2 transition-all cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCwIcon className="w-3.5 h-3.5 animate-spin" />
                  <span>EXECUTING...</span>
                </>
              ) : (
                <>
                  <span>RUN QUERY</span>
                  <span className="text-[10px] opacity-70">↵</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs font-mono flex items-start gap-3">
          <AlertTriangleIcon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">Execution Failed</p>
            <p className="text-slate-300">{error}</p>
            <p className="text-[11px] text-slate-400">
              Check that the AWS EC2 instance is reachable at the configured URL or check your X-API-Key header.
            </p>
          </div>
        </div>
      )}

      {/* Main Response Area */}
      {response && (
        <div className="space-y-6">
          {/* Status Header: Route + Step Trace */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {getRouteBadge(response.route, response.answered)}
                {response.tickers && response.tickers.length > 0 && (
                  <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                    <span>Ticker(s):</span>
                    <span className="text-emerald-400 font-bold">[{response.tickers.join(', ')}]</span>
                  </span>
                )}
                {response.fiscal_years && response.fiscal_years.length > 0 && (
                  <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                    <span>FY:</span>
                    <span className="text-sky-300 font-bold">{response.fiscal_years.join(', ')}</span>
                  </span>
                )}
              </div>

              {/* Telemetry Chips */}
              <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                  <ClockIcon className="w-3 h-3 text-slate-400" />
                  <span>{response.latency_ms} ms</span>
                </span>
                <span className="flex items-center gap-1 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 hidden sm:flex">
                  <CpuIcon className="w-3 h-3 text-slate-400" />
                  <span>{response.model || 'LLM'}</span>
                </span>
                <span className="flex items-center gap-1 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 hidden md:flex">
                  <HashIcon className="w-3 h-3 text-slate-400" />
                  <span>{response.input_tokens + response.output_tokens} tok</span>
                </span>
              </div>
            </div>

            {/* Execution Trace Pipeline */}
            {response.steps && response.steps.length > 0 && (
              <div className="pt-2 border-t border-slate-800/80">
                <span className="text-[10px] uppercase font-mono text-slate-500 block mb-1">
                  LangGraph Orchestration Trace:
                </span>
                <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono text-slate-300">
                  {response.steps.map((st, i) => (
                    <React.Fragment key={i}>
                      <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300">
                        {st}
                      </span>
                      {i < response.steps.length - 1 && <span className="text-slate-600">→</span>}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Grounded Synthesis Card */}
          <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 relative space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
                <span>Audited Answer (Citations Linked)</span>
              </span>
              <button
                onClick={() => handleCopy(response.answer)}
                className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 p-1 rounded hover:bg-slate-800 transition-colors"
                title="Copy Answer"
              >
                {copiedAnswer ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
                <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {/* Answer Text */}
            <div className="text-slate-100 text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {response.answered ? (
                renderCitationText(response.answer)
              ) : (
                <div className="space-y-2">
                  <p className="text-rose-300 font-mono font-semibold">
                    {response.answer || 'Not found in the indexed filings.'}
                  </p>
                  {response.reason && (
                    <p className="text-xs text-slate-400 font-mono">
                      Refusal Reason: <span className="text-slate-200">{response.reason}</span>
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Guardrail Warnings Banner if any */}
            {response.warnings && Object.keys(response.warnings).length > 0 && (
              <div className="mt-4 p-3 rounded-lg bg-amber-950/40 border border-amber-800/80 text-amber-300 text-xs font-mono space-y-1">
                <div className="flex items-center gap-1.5 font-bold">
                  <AlertTriangleIcon className="w-4 h-4 text-amber-400" />
                  <span>Automated Factuality & Citation Verification Warnings</span>
                </div>
                {response.warnings.uncited_sentences && (
                  <p className="text-[11px] text-slate-300">
                    • Uncited sentences detected: {response.warnings.uncited_sentences.join('; ')}
                  </p>
                )}
                {response.warnings.unsupported_numbers && (
                  <p className="text-[11px] text-slate-300">
                    • Figures not found in evidence rows: {response.warnings.unsupported_numbers.join(', ')}
                  </p>
                )}
                {response.warnings.truncated && (
                  <p className="text-[11px] text-amber-400">
                    • Warning: Response truncated at max output tokens!
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Evidence Inspection Tabs */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              <button
                onClick={() => setActiveTab('evidence')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                  activeTab === 'evidence'
                    ? 'bg-slate-800 text-emerald-400 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All Evidence
              </button>
              {response.table && (
                <button
                  onClick={() => setActiveTab('table')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-colors ${
                    activeTab === 'table'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <DatabaseIcon className="w-3.5 h-3.5 text-emerald-400" />
                  <span>SQL Table [T]</span>
                </button>
              )}
              {response.passages && response.passages.length > 0 && (
                <button
                  onClick={() => setActiveTab('passages')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-colors ${
                    activeTab === 'passages'
                      ? 'bg-sky-950 text-sky-300 border border-sky-800 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileTextIcon className="w-3.5 h-3.5 text-sky-400" />
                  <span>Passages ({response.passages.length})</span>
                </button>
              )}
            </div>

            {/* Tab: Structured SQL Table */}
            {(activeTab === 'evidence' || activeTab === 'table') && response.table && (
              <div
                className={`p-5 rounded-xl bg-slate-900 border transition-all ${
                  highlightedTable ? 'border-emerald-500 ring-2 ring-emerald-500/30' : 'border-slate-800'
                } space-y-4`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
                      Citation [T]
                    </span>
                    <span className="text-xs font-mono text-slate-300 font-semibold">
                      Executed SQL Result Set ({response.table.rows.length} rows)
                    </span>
                  </div>
                  <button
                    onClick={() => handleCopy(response.table?.sql || '', true)}
                    className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 p-1 rounded hover:bg-slate-800 transition-colors"
                  >
                    {copiedSql ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
                    <span>{copiedSql ? 'SQL Copied' : 'Copy SQL'}</span>
                  </button>
                </div>

                {/* SQL Query Snippet */}
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 overflow-x-auto">
                  <pre className="text-xs font-mono text-emerald-400/90 whitespace-pre-wrap leading-relaxed">
                    {response.table.sql}
                  </pre>
                </div>

                {/* Rows Table */}
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                      <tr>
                        {response.table.columns.map((col, i) => (
                          <th key={i} className="px-3 py-2.5 font-semibold">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                      {response.table.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-800/50 transition-colors">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="px-3 py-2 text-slate-200 whitespace-nowrap">
                              {cell === null ? (
                                <span className="text-slate-500 italic">NULL</span>
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

                {/* Source Filings */}
                {response.table.source_filings && response.table.source_filings.length > 0 && (
                  <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
                    <span>Source Accession:</span>
                    {response.table.source_filings.map((acc, aIdx) => (
                      <span key={aIdx} className="text-slate-200 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        {acc}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab: Filing Source Passages */}
            {(activeTab === 'evidence' || activeTab === 'passages') && response.passages && response.passages.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
                  <span>Retrieved Passages ({response.passages.length} Candidates Re-ranked)</span>
                  <span>Scored by Cross-Encoder</span>
                </div>

                <div className="space-y-3">
                  {response.passages.map((p: Passage) => {
                    const isHighlighted = highlightedPassage === p.n;
                    return (
                      <div
                        key={p.n}
                        id={`passage-${p.n}`}
                        className={`p-4 rounded-xl bg-slate-900/70 border transition-all ${
                          isHighlighted
                            ? 'border-sky-400 ring-2 ring-sky-500/30'
                            : p.cited
                            ? 'border-slate-700/80'
                            : 'border-slate-800/60 opacity-80'
                        } space-y-2.5`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-sky-950 text-sky-300 border border-sky-700">
                              [{p.n}]
                            </span>
                            {p.cited ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                                CITED IN ANSWER
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
                                CONSIDERED
                              </span>
                            )}
                            <span className="text-xs font-mono font-semibold text-slate-200">
                              {p.header}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                            <span>Score: <span className="text-sky-300 font-semibold">{p.score}</span></span>
                            {p.url && (
                              <a
                                href={p.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 hover:underline"
                              >
                                <span>SEC Source</span>
                                <ExternalLinkIcon className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        </div>

                        {/* Passage Text */}
                        <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-sans">
                          {p.text}
                        </div>

                        {/* Metadata Footer */}
                        <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
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
