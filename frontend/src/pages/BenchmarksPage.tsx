import React from 'react';
import { PageHeader, Section, Stat, StatRow } from '../components/common/ui';

const RETRIEVAL = [
  { name: 'Dense search', setting: 'Open', r1: '57.3', r5: '84.1', r10: '90.2', mrr: '0.682' },
  { name: 'Dense + rerank', setting: 'Open', r1: '84.1', r5: '95.1', r10: '96.3', mrr: '0.890', prod: true },
  { name: 'Dense search', setting: 'Company + year', r1: '61.0', r5: '90.2', r10: '96.3', mrr: '0.727' },
  { name: 'Dense + rerank', setting: 'Company + year', r1: '86.6', r5: '98.8', r10: '100.0', mrr: '0.920', prod: true },
];

const BM25 = [
  { label: 'LLM-written questions', overlap: '0.67', value: 82.9 },
  { label: 'Paraphrased questions', overlap: '0.16', value: 22.0 },
];

const Row: React.FC<{ label: string; value: string; note?: string }> = ({ label, value, note }) => (
  <div className="flex items-baseline justify-between gap-4 py-3 border-b border-rule">
    <span className="text-sm text-ink-2">
      {label}
      {note && <span className="text-muted"> · {note}</span>}
    </span>
    <span className="font-mono text-sm tabular whitespace-nowrap">{value}</span>
  </div>
);

export const BenchmarksPage: React.FC = () => (
  <div>
    <PageHeader eyebrow="Evaluation" title="Measured, including what didn’t work">
      Retrieval, text-to-SQL and routing are each scored on questions with known answers. Variants that made
      results worse were removed.
    </PageHeader>

    <StatRow>
      <Stat value="95.1%" label="Recall@5, reranked" note="82 paraphrased questions, no filters" />
      <Stat value="98.8%" label="Recall@5, routed" note="With the router’s company and year" />
      <Stat value="93.5%" label="Text-to-SQL accuracy" note="43 of 46, first run" />
      <Stat value="15/15" label="Unanswerable declined" note="End to end" />
    </StatRow>

    <Section
      title="Retrieval"
      description="82 questions worded differently from the passage that answers them, searched across all 11,540 chunks."
      aside={<span className="text-xs text-muted">Rerank vs dense: exact sign test, p = 0.004</span>}
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="text-left text-xs text-muted border-b border-rule-strong">
              <th className="font-medium py-2.5 pr-4">Retriever</th>
              <th className="font-medium py-2.5 pr-4">Filter</th>
              <th className="font-medium py-2.5 pr-4 text-right">R@1</th>
              <th className="font-medium py-2.5 pr-4 text-right">R@5</th>
              <th className="font-medium py-2.5 pr-4 text-right">R@10</th>
              <th className="font-medium py-2.5 text-right">MRR@10</th>
            </tr>
          </thead>
          <tbody className="font-mono text-sm tabular">
            {RETRIEVAL.map((r, i) => (
              <tr key={i} className={`border-b border-rule ${r.prod ? 'text-ink' : 'text-muted'}`}>
                <td className="py-3 pr-4 font-sans text-sm">
                  {r.name}
                  {r.prod && <span className="ml-2 text-xs text-accent">in production</span>}
                </td>
                <td className="py-3 pr-4 font-sans text-sm">{r.setting}</td>
                <td className="py-3 pr-4 text-right">{r.r1}%</td>
                <td className={`py-3 pr-4 text-right ${r.prod ? 'font-medium' : ''}`}>{r.r5}%</td>
                <td className="py-3 pr-4 text-right">{r.r10}%</td>
                <td className="py-3 text-right">{r.mrr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>

    <Section
      title="Why keyword search was removed"
      description="When an LLM writes questions while reading a passage, it reuses the passage’s words. That flatters BM25."
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-x-12 gap-y-8">
        <div className="space-y-5">
          {BM25.map((b) => (
            <div key={b.label}>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-ink-2">
                  {b.label} <span className="text-muted">· word overlap {b.overlap}</span>
                </span>
                <span className="font-mono tabular">{b.value.toFixed(1)}%</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-sunken overflow-hidden">
                <div className="h-full rounded-full bg-ink" style={{ width: `${b.value}%` }} />
              </div>
            </div>
          ))}
          <p className="text-xs text-muted">BM25 Recall@5 on the same 82 questions, before and after paraphrasing.</p>
        </div>
        <p className="text-sm leading-relaxed text-ink-2">
          Paraphrasing the questions cut word overlap from 0.67 to 0.16, and BM25 fell from 82.9% to 22.0%. Fusing it
          with dense search (reciprocal rank fusion) then lowered Recall@5 from 84.1% to 61.0%, so BM25 was removed.
          The paraphrased set became the headline benchmark.
        </p>
      </div>
    </Section>

    <section className="py-10 grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Text-to-SQL</h2>
        <p className="mt-1 mb-4 text-sm text-muted">Execution accuracy: results compared with gold queries.</p>
        <Row label="First run" value="43 / 46 · 93.5%" />
        <Row label="Out-of-scope questions declined" value="10 / 10" />
        <Row label="After fixes" note="tuned on the same set" value="46 / 46" />
      </div>
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Routing</h2>
        <p className="mt-1 mb-4 text-sm text-muted">151 questions with a known correct route.</p>
        <Row label="Routed correctly" value="142 / 151 · 94.0%" />
        <Row label="Hybrid questions" value="15 / 15" />
        <Row label="Answerable but declined" note="MPLX subsidiary" value="1 / 138" />
      </div>
    </section>
  </div>
);
