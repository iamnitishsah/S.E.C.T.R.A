import React from 'react';
import { PageHeader, Section, Code } from '../components/common/ui';

const STEPS = [
  {
    name: 'Router',
    tech: 'LLM + catalog',
    color: 'bg-ink',
    body: (
      <>
        Picks a route (<Code>sql</Code>, <Code>text</Code>, <Code>both</Code> or <Code>none</Code>) and extracts the
        companies and fiscal years. A deterministic check against the catalog then declines anything not indexed.
      </>
    ),
  },
  {
    name: 'SQL',
    tech: 'MySQL 8.4',
    color: 'bg-sql',
    body: 'Writes one SELECT, which is parsed, validated and run as a read-only user with a 5-second timeout and a 200-row cap.',
  },
  {
    name: 'Text',
    tech: 'Qdrant + reranker',
    color: 'bg-text',
    body: 'Dense search over 1,024-d vectors returns 60 candidates; a hosted reranker keeps the top 5. A score gate (0.042) stops weak matches before any LLM call.',
  },
  {
    name: 'Writer',
    tech: 'LLM + checks',
    color: 'bg-both',
    body: (
      <>
        Writes the answer citing <Code>[T]</Code> for table rows and <Code>[n]</Code> for passages, then checks that
        every citation exists and every number appears in the evidence.
      </>
    ),
  },
];

const SQL_LAYERS = [
  {
    title: 'A read-only database user',
    body: (
      <>
        <Code>sectra_reader</Code> can only SELECT from <Code>financial_metrics</Code>, <Code>companies</Code> and{' '}
        <Code>filings</Code>. This holds even if a validator rule is wrong.
      </>
    ),
  },
  {
    title: 'A parser, not a regex',
    body: (
      <>
        Queries are parsed with sqlglot and regenerated from the tree, which strips comments (including MySQL’s{' '}
        <Code>/*! … */</Code>). Unknown functions such as <Code>SLEEP()</Code> and <Code>BENCHMARK()</Code> are
        rejected.
      </>
    ),
  },
];

const REFUSAL = [
  {
    n: 8,
    title: 'Router and catalog',
    body: 'Unindexed companies, missing years, forecasts and advice are declined before any search runs.',
  },
  {
    n: 4,
    title: 'Evidence check',
    body: 'When the best passage scores below the threshold, as with odd questions about indexed companies, no LLM is called.',
  },
  {
    n: 3,
    title: 'Writer',
    body: 'When passages look related but don’t support the premise, the writer answers NOT_FOUND instead of guessing.',
  },
];

const DEPLOYMENT = [
  ['Hosting', 'One AWS EC2 instance (t3.small, Ubuntu) runs FastAPI, MySQL and Qdrant with Docker Compose.'],
  ['Network', 'MySQL and Qdrant bind to 127.0.0.1; only the API on port 8000 is exposed.'],
  ['Frontend', 'Served by Vercel, which proxies /api requests to the EC2 instance.'],
  ['CI/CD', 'GitHub Actions runs 154 unit tests on every push to main, then deploys over SSH and waits for /health.'],
];

export const ArchitecturePage: React.FC = () => (
  <div>
    <PageHeader eyebrow="How it works" title="Four steps from question to cited answer">
      A LangGraph graph routes each question, gathers evidence from the database and the filings, and writes an answer
      that can only use that evidence.
    </PageHeader>

    <Section title="The query graph">
      <ol className="relative">
        {STEPS.map((s, i) => (
          <li key={s.name} className="relative grid grid-cols-[2rem_1fr] sm:grid-cols-[2rem_10rem_1fr] gap-x-4 pb-8 last:pb-0">
            {i < STEPS.length - 1 && <span className="absolute left-[0.6875rem] top-6 bottom-0 w-px bg-rule-strong" />}
            <span className="relative mt-1 w-6 h-6 rounded-full bg-bg border border-rule-strong grid place-items-center">
              <span className={`w-2 h-2 rounded-full ${s.color}`} />
            </span>
            <div className="mb-1 sm:mb-0">
              <div className="font-medium">{s.name}</div>
              <div className="text-xs text-muted">{s.tech}</div>
            </div>
            <p className="col-start-2 sm:col-start-3 text-sm leading-relaxed text-ink-2 max-w-2xl">{s.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-10 pl-5 border-l-2 border-both max-w-2xl">
        <p className="text-sm font-medium">When a question names no company</p>
        <p className="mt-1.5 text-sm leading-relaxed text-muted">
          For <em>“Which healthcare company grew revenue fastest in 2025, and what drove that growth?”</em> the SQL
          step runs first and finds Eli Lilly. The text search is then filtered to LLY’s FY2025 filing, so passages from
          other companies can’t crowd it out.
        </p>
      </div>
    </Section>

    <Section title="Generated SQL is checked twice">
      <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-7">
        {SQL_LAYERS.map((l, i) => (
          <div key={l.title}>
            <dt className="flex items-baseline gap-3">
              <span className="font-mono text-xs text-faint">0{i + 1}</span>
              <span className="font-medium">{l.title}</span>
            </dt>
            <dd className="mt-1.5 pl-8 text-sm leading-relaxed text-muted">{l.body}</dd>
          </div>
        ))}
      </dl>
    </Section>

    <Section
      title="Three layers decline what can’t be answered"
      description="Of 15 unanswerable test questions, each layer caught the number shown. None got through."
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-10 gap-y-8">
        {REFUSAL.map((r) => (
          <div key={r.title}>
            <div className="flex items-baseline gap-2">
              <span className="font-serif text-4xl leading-none tabular">{r.n}</span>
              <span className="text-xs text-muted">of 15</span>
            </div>
            <p className="mt-3 font-medium">{r.title}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{r.body}</p>
          </div>
        ))}
      </div>
    </Section>

    <Section title="Deployment">
      <dl className="divide-y divide-rule border-y border-rule">
        {DEPLOYMENT.map(([k, v]) => (
          <div key={k} className="grid grid-cols-1 sm:grid-cols-[10rem_1fr] gap-1 sm:gap-4 py-3.5">
            <dt className="text-sm font-medium">{k}</dt>
            <dd className="text-sm text-muted">{v}</dd>
          </div>
        ))}
      </dl>
    </Section>
  </div>
);
