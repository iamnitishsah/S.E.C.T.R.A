import React, { useState, useEffect } from 'react';
import type { Company } from '../types/api';
import type { NavTab } from '../components/layout/Header';
import { fetchCompanies } from '../services/api';
import { SearchIcon, ArrowRightIcon } from '../components/common/Icons';
import { Section, Stat, StatRow, Code } from '../components/common/ui';

const PILLARS = [
  {
    n: '01',
    title: 'Figures come from a database',
    body: 'XBRL facts from every filing are loaded into MySQL and normalized into 15 canonical metrics. A text-to-SQL agent queries them through a parser-validated, read-only connection.',
  },
  {
    n: '02',
    title: 'Explanations come from the filings',
    body: '10-K text is split by Item and indexed in Qdrant. Dense search returns 60 candidates, a reranker keeps the best 5, and every sentence in the answer cites one.',
  },
  {
    n: '03',
    title: 'A router decides which to use',
    body: 'A LangGraph router sends each question to the database, the filing text or both, and declines questions about companies or years that are not indexed.',
  },
];

const DATA_NOTES = [
  {
    title: 'Restatements replace older numbers',
    body: 'Each 10-K repeats the two prior years. The latest filing wins, so a restated figure overrides the original.',
  },
  {
    title: 'Fiscal years are derived, not trusted',
    body: (
      <>
        Computed as <Code>YEAR(period_end − 7d) + offset</Code>. SEC’s own <Code>fy</Code> field mislabels some
        NVIDIA filings, and 52/53-week years need the adjustment.
      </>
    ),
  },
  {
    title: 'The same tag can mean different things',
    body: (
      <>
        Chevron’s <Code>Revenues</Code> includes other income; ConocoPhillips’ does not. Company-specific overrides
        resolve it.
      </>
    ),
  },
  {
    title: 'CIK is the identity, not the ticker',
    body: 'Tickers move during reorganizations (Exxon Mobil, 2026). Every table and vector payload is keyed by CIK.',
  },
];

export const OverviewPage: React.FC<{ onNavigate: (tab: NavTab) => void }> = ({ onNavigate }) => {
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
      setError(err instanceof Error ? err.message : 'Failed to load the company list');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  const sectors = ['all', ...Array.from(new Set(companies.map((c) => c.sector.toLowerCase()))).sort()];
  const q = searchQuery.toLowerCase();
  const filtered = companies.filter(
    (c) =>
      (sectorFilter === 'all' || c.sector.toLowerCase() === sectorFilter) &&
      (c.ticker.toLowerCase().includes(q) || c.name.toLowerCase().includes(q))
  );

  return (
    <div>
      {/* Hero */}
      <section className="pb-14">
        <p className="text-xs font-medium text-muted uppercase tracking-[0.12em]">SEC 10-K research system</p>
        <h1 className="mt-4 font-serif text-[3rem] sm:text-[4.5rem] leading-[1.02] tracking-[-0.015em] max-w-6xl">
          Answers from annual reports, with every source attached.
        </h1>
        <p className="mt-6 text-xl leading-relaxed text-ink-2 max-w-3xl">
          Language models invent numbers, do arithmetic badly and can’t say where a claim came from. S.E.C.T.R.A
          never lets the model answer from memory: figures come from database rows, explanations from cited filing
          passages, and when the evidence isn’t there it says so.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button
            onClick={() => onNavigate('demo')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-ink text-bg text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Ask a question
            <ArrowRightIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => onNavigate('benchmarks')}
            className="px-4 py-2.5 rounded-lg text-sm text-ink-2 hover:text-ink hover:bg-surface border border-transparent hover:border-rule transition-colors"
          >
            See the evaluation
          </button>
        </div>
      </section>

      <div className="border-t border-rule">
        <StatRow>
          <Stat value="20" label="Companies" note="Four sectors" />
          <Stat value="80" label="Annual reports" note="Form 10-K" />
          <Stat value="534K" label="XBRL facts" note="534,026 loaded" />
          <Stat value="11,540" label="Text chunks" note="Indexed for retrieval" />
        </StatRow>
      </div>

      <Section title="Each question goes to the source that can answer it">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-x-16 gap-y-8">
          {PILLARS.map((p) => (
            <div key={p.n}>
              <div className="font-mono text-xs text-faint">{p.n}</div>
              <h3 className="mt-2 font-medium text-ink">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{p.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section
        title="Companies"
        description={
          <>
            Loaded live from <Code>GET /companies</Code>.
          </>
        }
        aside={
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <SearchIcon className="w-3.5 h-3.5 text-faint absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search"
                className="w-56 bg-surface border border-rule rounded-lg pl-8 pr-3 py-1.5 text-sm placeholder:text-faint focus:outline-none focus:border-rule-strong"
              />
            </div>
            {sectors.length > 1 && (
              <div className="flex items-center gap-1 text-sm">
                {sectors.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSectorFilter(s)}
                    className={`px-2.5 py-1 rounded-md capitalize transition-colors ${
                      sectorFilter === s ? 'bg-ink text-bg' : 'text-muted hover:text-ink'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        }
      >
        {loading && (
          <div className="space-y-px">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-11 bg-surface/60 animate-pulse" />
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="rounded-lg bg-danger-soft text-danger px-4 py-3 text-sm flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">Couldn’t load companies</p>
              <p className="text-xs opacity-80 mt-0.5">{error}. Check the API key in the header.</p>
            </div>
            <button onClick={loadCompanies} className="underline underline-offset-2">
              Retry
            </button>
          </div>
        )}

        {!loading && !error && companies.length === 0 && (
          <p className="text-sm text-muted">No companies were returned.</p>
        )}

        {!loading && !error && companies.length > 0 && (
          <div className="overflow-x-auto -mx-6 sm:mx-0">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="text-left text-xs text-muted border-b border-rule-strong">
                  <th className="font-medium py-2.5 pl-6 sm:pl-0 pr-4">Ticker</th>
                  <th className="font-medium py-2.5 pr-4">Company</th>
                  <th className="font-medium py-2.5 pr-4">Sector</th>
                  <th className="font-medium py-2.5 pr-4">Metrics</th>
                  <th className="font-medium py-2.5 pr-6 sm:pr-0">Filing text</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-muted">
                      Nothing matches.
                    </td>
                  </tr>
                ) : (
                  filtered.map((c) => (
                    <tr key={c.ticker} className="border-b border-rule hover:bg-surface/70 transition-colors">
                      <td className="py-3 pl-6 sm:pl-0 pr-4 font-mono font-medium">{c.ticker}</td>
                      <td className="py-3 pr-4 text-ink-2">{c.name}</td>
                      <td className="py-3 pr-4 text-muted capitalize">{c.sector}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-muted tabular">
                        {c.metric_years?.length === 2
                          ? `${c.metric_years[0]}–${c.metric_years[1]}`
                          : c.metric_years?.join(', ') || '—'}
                      </td>
                      <td className="py-3 pr-6 sm:pr-0 font-mono text-xs tabular">
                        {c.text_years?.length ? (
                          <span className="text-muted">{c.text_years.map((y) => `FY${String(y).slice(2)}`).join('  ')}</span>
                        ) : (
                          <span className="text-warn">Metrics only</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            <p className="mt-3 px-6 sm:px-0 text-xs text-faint">
              {filtered.length} of {companies.length} companies
            </p>
          </div>
        )}
      </Section>

      <Section title="Notes on the data" description="Problems found in SEC data, and how the database handles them.">
        <dl className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-x-12 gap-y-8">
          {DATA_NOTES.map((n) => (
            <div key={n.title}>
              <dt className="font-medium text-ink">{n.title}</dt>
              <dd className="mt-1.5 text-sm leading-relaxed text-muted">{n.body}</dd>
            </div>
          ))}
        </dl>
      </Section>
    </div>
  );
};
