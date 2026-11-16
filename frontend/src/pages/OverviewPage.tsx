import React, { useState, useEffect } from 'react';
import type { Company } from '../types/api';
import { fetchCompanies } from '../services/api';
import {
  DatabaseIcon,
  FileTextIcon,
  LayersIcon,
  SearchIcon,
  CheckIcon,
  AlertTriangleIcon,
  BarChart3Icon,
  ZapIcon
} from '../components/common/Icons';

// Fallback dataset when backend is not reached yet
const FALLBACK_COMPANIES: Company[] = [
  { ticker: 'AAPL', name: 'Apple Inc.', sector: 'technology', text_years: [2023, 2024, 2025, 2026], metric_years: [2009, 2026] },
  { ticker: 'MSFT', name: 'MICROSOFT CORP', sector: 'technology', text_years: [2023, 2024, 2025, 2026], metric_years: [2009, 2026] },
  { ticker: 'GOOGL', name: 'Alphabet Inc.', sector: 'technology', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'AMZN', name: 'AMAZON COM INC', sector: 'technology', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'META', name: 'Meta Platforms, Inc.', sector: 'technology', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'NVDA', name: 'NVIDIA CORP', sector: 'semiconductors', text_years: [2023, 2024, 2025, 2026], metric_years: [2009, 2026] },
  { ticker: 'AMD', name: 'ADVANCED MICRO DEVICES INC', sector: 'semiconductors', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'INTC', name: 'INTEL CORP', sector: 'semiconductors', text_years: [], metric_years: [2009, 2025] },
  { ticker: 'QCOM', name: 'QUALCOMM INC/DE', sector: 'semiconductors', text_years: [2023, 2024, 2025, 2026], metric_years: [2009, 2026] },
  { ticker: 'AVGO', name: 'Broadcom Inc.', sector: 'semiconductors', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'JNJ', name: 'JOHNSON & JOHNSON', sector: 'healthcare', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'PFE', name: 'PFIZER INC', sector: 'healthcare', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'MRK', name: 'Merck & Co., Inc.', sector: 'healthcare', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'ABBV', name: 'AbbVie Inc.', sector: 'healthcare', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'LLY', name: 'ELI LILLY & Co', sector: 'healthcare', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'CVX', name: 'CHEVRON CORP', sector: 'energy', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'COP', name: 'CONOCOPHILLIPS', sector: 'energy', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'EOG', name: 'EOG RESOURCES INC', sector: 'energy', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'MPC', name: 'Marathon Petroleum Corp', sector: 'energy', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
  { ticker: 'SLB', name: 'SLB LIMITED/NV', sector: 'energy', text_years: [2022, 2023, 2024, 2025], metric_years: [2009, 2025] },
];

export const OverviewPage: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>(FALLBACK_COMPANIES);
  const [loading, setLoading] = useState<boolean>(true);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [sectorFilter, setSectorFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchCompanies();
        if (mounted && Array.isArray(data) && data.length > 0) {
          setCompanies(data);
          setIsLive(true);
        }
      } catch {
        // keep fallback
        if (mounted) setIsLive(false);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  const sectors = ['all', 'technology', 'semiconductors', 'healthcare', 'energy'];

  const filteredCompanies = companies.filter((c) => {
    const matchesSector = sectorFilter === 'all' || c.sector.toLowerCase() === sectorFilter.toLowerCase();
    const matchesSearch =
      c.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSector && matchesSearch;
  });

  return (
    <div className="space-y-10 pb-16">
      {/* Hero Section */}
      <div className="border border-slate-800 rounded-2xl bg-gradient-to-b from-slate-900/80 via-slate-900/40 to-slate-950 p-6 sm:p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-3xl space-y-4 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs font-mono">
            <ZapIcon className="w-3.5 h-3.5 text-emerald-400" />
            <span>Strict Zero-Hallucination SEC EDGAR Engine</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-slate-100 font-mono">
            S.E.C.T.R.A
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            Securities & Exchange Commission Tracking, Retrieval & Analysis. A high-assurance research system over SEC EDGAR 10-K filings. 
            Numeric queries are answered from a validated relational financial database, narrative disclosures with cited RAG, and hybrid inquiries with both.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4">
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <span className="block text-xs font-mono text-slate-400">Indexed Universe</span>
              <span className="text-xl font-bold font-mono text-emerald-400">20 Companies</span>
              <span className="text-[11px] text-slate-500 block">4 Critical Sectors</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <span className="block text-xs font-mono text-slate-400">10-K Reports</span>
              <span className="text-xl font-bold font-mono text-sky-400">80 Filings</span>
              <span className="text-[11px] text-slate-500 block">313 MB Clean HTML</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <span className="block text-xs font-mono text-slate-400">XBRL Facts</span>
              <span className="text-xl font-bold font-mono text-emerald-400">534,026</span>
              <span className="text-[11px] text-slate-500 block">15 Canonical Metrics</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <span className="block text-xs font-mono text-slate-400">Text Chunks</span>
              <span className="text-xl font-bold font-mono text-sky-400">11,540</span>
              <span className="text-[11px] text-slate-500 block">Qdrant 1,024-d Vectors</span>
            </div>
          </div>
        </div>
      </div>

      {/* The 3-Pillar Solution Table */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <LayersIcon className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-slate-100 font-mono">The Tripartite Source-of-Truth Model</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Pillar 1: Financial Facts */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-3 relative overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-emerald-950/80 border border-emerald-600/40 flex items-center justify-center text-emerald-400">
              <DatabaseIcon className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-slate-100 text-sm font-mono flex items-center justify-between">
              <span>1. Exact Figures & Arithmetic</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/50">SQL</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Revenue, net income, EPS, cash flow, assets, capex. Facts in MySQL normalized into 15 canonical metrics. Handled by an AST-validated Text-to-SQL agent with zero mental math by the LLM.
            </p>
            <div className="pt-2 text-[11px] font-mono text-emerald-400/90 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5" />
              <span>93.5% First-run Execution Accuracy</span>
            </div>
          </div>

          {/* Pillar 2: Filing Text */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-3 relative overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-sky-950/80 border border-sky-600/40 flex items-center justify-center text-sky-400">
              <FileTextIcon className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-slate-100 text-sm font-mono flex items-center justify-between">
              <span>2. Explanations & Risks</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800/50">RAG</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Management discussion (MD&A Item 7), Risk Factors (Item 1A), Business (Item 1), Cybersecurity (Item 1C). Dense search in Qdrant + cross-encoder reranker with sentence-level citations.
            </p>
            <div className="pt-2 text-[11px] font-mono text-sky-400/90 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5" />
              <span>95.1% Recall@5 (98.8% Scoped)</span>
            </div>
          </div>

          {/* Pillar 3: LangGraph Synthesis */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-3 relative overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-amber-950/80 border border-amber-600/40 flex items-center justify-center text-amber-400">
              <LayersIcon className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-slate-100 text-sm font-mono flex items-center justify-between">
              <span>3. Hybrid Questions</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800/50">BOTH</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              "Which healthcare firm grew revenue fastest in 2025 and why?" Dynamic LangGraph orchestrator: SQL step identifies the firm, which automatically scopes the subsequent filing search.
            </p>
            <div className="pt-2 text-[11px] font-mono text-amber-400/90 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5" />
              <span>94.0% Routing Accuracy, 15/15 Refused</span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Company Catalog */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BarChart3Icon className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-slate-100 font-mono">
              Indexed Universe Catalog
            </h2>
            <span className="text-xs font-mono text-slate-400 ml-2">
              ({filteredCompanies.length} of {companies.length} displayed)
            </span>
            {isLive ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 ml-2">
                LIVE API
              </span>
            ) : loading ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 ml-2">
                LOADING...
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 ml-2">
                SNAPSHOT
              </span>
            )}
          </div>

          {/* Search & Sector Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <SearchIcon className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ticker or name..."
                className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-emerald-500 font-mono w-44"
              />
            </div>

            <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs">
              {sectors.map((sec) => (
                <button
                  key={sec}
                  onClick={() => setSectorFilter(sec)}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono capitalize transition-colors ${
                    sectorFilter === sec
                      ? 'bg-slate-800 text-emerald-400 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sec}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Company Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {filteredCompanies.map((c) => {
            const hasText = c.text_years && c.text_years.length > 0;
            return (
              <div
                key={c.ticker}
                className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-bold text-emerald-400 text-base">{c.ticker}</span>
                    <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                      {c.sector}
                    </span>
                  </div>
                  <h4 className="text-xs font-medium text-slate-200 truncate" title={c.name}>
                    {c.name}
                  </h4>
                </div>

                <div className="space-y-1.5 pt-2 border-t border-slate-800/80 text-[11px] font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Financial Metrics:</span>
                    <span className="text-slate-200">
                      {c.metric_years.length === 2 ? `${c.metric_years[0]}–${c.metric_years[1]}` : 'Historical'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span>10-K Filing Text:</span>
                    {hasText ? (
                      <span className="text-sky-300 font-semibold">
                        FY {c.text_years.join(', ')}
                      </span>
                    ) : (
                      <span className="text-amber-400/90 text-[10px] flex items-center gap-1" title="Intel cross-reference index format skipped">
                        <AlertTriangleIcon className="w-3 h-3 text-amber-400" />
                        <span>Metrics Only</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Engineering Decisions & Data Findings */}
      <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 space-y-4">
        <h3 className="text-sm font-bold font-mono text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <span>Key SEC Data Normalization Rules Enforced</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/60 space-y-1.5">
            <span className="font-mono text-emerald-400 font-semibold block">1. Restatements Overwrite Past Filings</span>
            <p className="text-slate-400 leading-relaxed">
              Every 10-K restates prior years. Under the `annual_facts` view, the latest filing accession wins, ensuring retroactive accounting adjustments automatically replace outdated figures.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/60 space-y-1.5">
            <span className="font-mono text-emerald-400 font-semibold block">2. Fiscal Year Offset Derivation</span>
            <p className="text-slate-400 leading-relaxed">
              Calculated via <code className="text-slate-300 font-mono">YEAR(year_end − 7d) + offset</code>. This eliminates errors caused by SEC's mislabeled `fy` field (e.g. NVIDIA FY2011–2014) and 52/53-week fiscal schedules.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/60 space-y-1.5">
            <span className="font-mono text-emerald-400 font-semibold block">3. Semantic Metric Disambiguation</span>
            <p className="text-slate-400 leading-relaxed">
              Chevron reported other income under `Revenues`, inflating top-line sales. S.E.C.T.R.A overrides it with contractual customer revenue mapped via <code className="text-slate-300 font-mono">metric_map.csv</code>.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/60 space-y-1.5">
            <span className="font-mono text-emerald-400 font-semibold block">4. CIK as Stable Immutable Key</span>
            <p className="text-slate-400 leading-relaxed">
              Tickers mutate during corporate reorganizations (e.g. Exxon Mobil 2026). CIK is enforced across all tables, schemas, and Qdrant chunk metadata.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
