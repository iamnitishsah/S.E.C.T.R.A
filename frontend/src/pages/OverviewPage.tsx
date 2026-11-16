import React, { useState, useEffect } from 'react';
import type { Company } from '../types/api';
import { fetchCompanies } from '../services/api';
import {
  DatabaseIcon,
  FileTextIcon,
  LayersIcon,
  SearchIcon,
  AlertTriangleIcon,
  RefreshCwIcon,
  CheckIcon
} from '../components/common/Icons';

export const OverviewPage: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadCompanies = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCompanies();
      setCompanies(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load company catalog from backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  // Dynamically extract unique sectors from the live API response
  const availableSectors = ['all', ...Array.from(new Set(companies.map((c) => c.sector.toLowerCase()))).sort()];

  const filteredCompanies = companies.filter((c) => {
    const matchesSector = sectorFilter === 'all' || c.sector.toLowerCase() === sectorFilter.toLowerCase();
    const matchesSearch =
      c.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSector && matchesSearch;
  });

  return (
    <div className="space-y-10 pb-16">
      {/* Executive Intro */}
      <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 sm:p-8 space-y-4">
        <div className="max-w-4xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-neutral-800/80 text-neutral-300 text-xs font-mono">
            SEC EDGAR Intelligence System
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight">
            Securities & Exchange Commission Tracking, Retrieval & Analysis
          </h1>
          <p className="text-sm text-neutral-300 leading-relaxed">
            S.E.C.T.R.A is a research system designed for SEC EDGAR 10-K filings. 
            Standard LLMs handle financial analysis poorly: they invent numbers, perform arithmetic unreliably, and cannot point to exact filing sections.
            S.E.C.T.R.A enforces a strict foundational principle: <strong>the LLM never supplies facts from memory</strong>.
          </p>
        </div>

        {/* The 3-Pillar Architecture Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-neutral-800/80">
          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold text-emerald-400">
              <DatabaseIcon className="w-4 h-4" />
              <span>1. Exact Figures & Arithmetic</span>
            </div>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Reported XBRL facts loaded into MySQL, normalized into 15 canonical metrics. Handled by an AST-validated text-to-SQL agent with a read-only database user.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold text-sky-400">
              <FileTextIcon className="w-4 h-4" />
              <span>2. Explanations & Risks</span>
            </div>
            <p className="text-xs text-neutral-400 leading-relaxed">
              10-K filing text extracted by Item and indexed in Qdrant (1,024-d vectors). High-precision retrieval through dense search followed by cross-encoder reranking.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold text-amber-400">
              <LayersIcon className="w-4 h-4" />
              <span>3. Hybrid Synthesis</span>
            </div>
            <p className="text-xs text-neutral-400 leading-relaxed">
              LangGraph state graph: router classifies incoming queries, verifies corpus availability, executes SQL, scopes narrative retrieval, and synthesizes answers with citations.
            </p>
          </div>
        </div>
      </div>

      {/* Dynamic Company Catalog (strictly from live backend API) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white tracking-tight">
              Indexed Company Universe
            </h2>
            <p className="text-xs text-neutral-400 mt-0.5">
              Live catalog fetched directly from the backend API (<code className="font-mono text-neutral-300">GET /companies</code>).
            </p>
          </div>

          {/* Search & Sector Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <SearchIcon className="w-3.5 h-3.5 text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ticker or name..."
                className="bg-[#101318] border border-neutral-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-hidden focus:border-neutral-600 font-mono w-48 transition-colors"
              />
            </div>

            {availableSectors.length > 1 && (
              <div className="flex items-center gap-1 bg-[#101318] p-1 rounded-lg border border-neutral-800 text-xs">
                {availableSectors.map((sec) => (
                  <button
                    key={sec}
                    onClick={() => setSectorFilter(sec)}
                    className={`px-2.5 py-1 rounded text-[11px] font-mono capitalize transition-colors ${
                      sectorFilter === sec
                        ? 'bg-neutral-800 text-white font-medium'
                        : 'text-neutral-400 hover:text-neutral-200'
                    }`}
                  >
                    {sec}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Live Loading State */}
        {loading && (
          <div className="p-12 border border-neutral-800 rounded-xl bg-[#101318] flex flex-col items-center justify-center gap-3 text-neutral-400 text-xs">
            <RefreshCwIcon className="w-5 h-5 animate-spin text-neutral-300" />
            <span>Loading company catalog from backend...</span>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="p-6 border border-neutral-800 rounded-xl bg-[#101318] space-y-3">
            <div className="flex items-start gap-3">
              <AlertTriangleIcon className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-xs font-semibold text-neutral-200">Unable to load company catalog from backend</p>
                <p className="text-xs text-neutral-400 font-mono">{error}</p>
                <p className="text-xs text-neutral-500">
                  Verify that your backend endpoint is reachable and check your X-API-Key setting.
                </p>
              </div>
            </div>
            <button
              onClick={loadCompanies}
              className="px-3 py-1.5 rounded bg-neutral-800 hover:bg-neutral-700 text-xs font-medium text-neutral-200 flex items-center gap-1.5 transition-colors"
            >
              <RefreshCwIcon className="w-3.5 h-3.5" />
              <span>Retry Request</span>
            </button>
          </div>
        )}

        {/* Live Data Table */}
        {!loading && !error && companies.length > 0 && (
          <div className="border border-neutral-800 rounded-xl overflow-hidden bg-[#101318]">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0c0e12] border-b border-neutral-800 text-neutral-400 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3 font-medium">Ticker</th>
                    <th className="px-4 py-3 font-medium">Company Name</th>
                    <th className="px-4 py-3 font-medium">Sector</th>
                    <th className="px-4 py-3 font-medium">Financial Metrics History</th>
                    <th className="px-4 py-3 font-medium">10-K Filing Text Indexed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60 font-sans">
                  {filteredCompanies.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-neutral-500 text-xs">
                        No companies match your search or filter.
                      </td>
                    </tr>
                  ) : (
                    filteredCompanies.map((c) => {
                      const hasText = c.text_years && c.text_years.length > 0;
                      return (
                        <tr key={c.ticker} className="hover:bg-neutral-800/30 transition-colors">
                          <td className="px-4 py-3 font-mono font-bold text-white">
                            {c.ticker}
                          </td>
                          <td className="px-4 py-3 text-neutral-200 font-medium">
                            {c.name}
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono capitalize bg-neutral-800 text-neutral-300">
                              {c.sector}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-neutral-300 text-xs">
                            {c.metric_years && c.metric_years.length === 2
                              ? `${c.metric_years[0]} – ${c.metric_years[1]}`
                              : c.metric_years?.length ? c.metric_years.join(', ') : 'N/A'}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">
                            {hasText ? (
                              <div className="flex flex-wrap gap-1">
                                {c.text_years.map((yr) => (
                                  <span key={yr} className="px-1.5 py-0.5 rounded text-[10px] bg-neutral-800/80 text-neutral-300">
                                    FY{yr}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-amber-400/90 text-[11px] font-sans">
                                Metrics Only (Cross-ref index)
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            <div className="px-4 py-3 bg-[#0c0e12] border-t border-neutral-800 flex items-center justify-between text-[11px] text-neutral-500 font-mono">
              <span>Showing {filteredCompanies.length} of {companies.length} companies</span>
              <span>Loaded from live catalog</span>
            </div>
          </div>
        )}

        {/* Empty Catalog Response */}
        {!loading && !error && companies.length === 0 && (
          <div className="p-8 border border-neutral-800 rounded-xl bg-[#101318] text-center text-xs text-neutral-400">
            No companies were returned by the backend catalog.
          </div>
        )}
      </div>

      {/* Core Engineering Decisions & Rules */}
      <div className="border border-neutral-800 rounded-xl p-6 bg-[#101318] space-y-4">
        <h3 className="text-sm font-semibold text-white tracking-tight">
          SEC Data Normalization Principles
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800/80 space-y-1.5">
            <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              <span>Restatements Automatically Overwrite Past Filings</span>
            </div>
            <p className="text-neutral-400 leading-relaxed">
              Every 10-K repeats the prior two years as comparatives. Under the database views, the latest filing accession wins, ensuring retroactive restatements replace older numbers automatically.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800/80 space-y-1.5">
            <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              <span>Fiscal Year Derivation</span>
            </div>
            <p className="text-neutral-400 leading-relaxed">
              Derived via <code className="font-mono text-neutral-300">YEAR(year_end − 7d) + company_offset</code>. This corrects cases where the SEC's own <code className="font-mono text-neutral-300">fy</code> field is mislabeled and handles 52/53-week fiscal schedules.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800/80 space-y-1.5">
            <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              <span>Semantic Tag Disambiguation</span>
            </div>
            <p className="text-neutral-400 leading-relaxed">
              Chevron's raw <code className="font-mono text-neutral-300">Revenues</code> concept includes other income, whereas ConocoPhillips' does not. S.E.C.T.R.A resolves this through prioritized tag mapping with company-specific overrides.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800/80 space-y-1.5">
            <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
              <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              <span>CIK Enforced as Primary Key</span>
            </div>
            <p className="text-neutral-400 leading-relaxed">
              Tickers fluctuate or transfer during corporate reorganizations (such as Exxon Mobil in 2026). The zero-padded CIK is enforced across all tables, schemas, and vector payloads.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
