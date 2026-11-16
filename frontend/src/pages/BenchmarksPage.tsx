import React from 'react';
import {
  BarChart3Icon,
  DatabaseIcon,
  FileTextIcon,
  LayersIcon,
  ZapIcon
} from '../components/common/Icons';

export const BenchmarksPage: React.FC = () => {
  return (
    <div className="space-y-10 pb-20">
      {/* Header */}
      <div className="space-y-2 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2">
          <BarChart3Icon className="w-5 h-5 text-emerald-400" />
          <h2 className="text-xl font-bold text-slate-100 font-mono">Empirical Evaluation & Benchmark Results</h2>
        </div>
        <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
          Comprehensive quantitative verification of retrieval recall, text-to-SQL execution accuracy, router classification, and end-to-end unanswerable question refusal.
        </p>
      </div>

      {/* Headline Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-xs font-mono text-slate-400">Reranked Recall@5</span>
          <div className="text-2xl font-bold font-mono text-emerald-400">95.1%</div>
          <p className="text-[11px] text-slate-500 font-mono">82 paraphrased questions (Open)</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-xs font-mono text-slate-400">Scoped Recall@5</span>
          <div className="text-2xl font-bold font-mono text-sky-400">98.8%</div>
          <p className="text-[11px] text-slate-500 font-mono">With company/year filter</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-xs font-mono text-slate-400">Text-to-SQL Accuracy</span>
          <div className="text-2xl font-bold font-mono text-emerald-400">93.5%</div>
          <p className="text-[11px] text-slate-500 font-mono">43/46 on first run (46/46 tuned)</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-xs font-mono text-slate-400">Unanswerable Refusal</span>
          <div className="text-2xl font-bold font-mono text-emerald-400">15 / 15</div>
          <p className="text-[11px] text-slate-500 font-mono">100% end-to-end refusal</p>
        </div>
      </div>

      {/* Retrieval Experiment Table */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileTextIcon className="w-5 h-5 text-sky-400" />
            <h3 className="font-mono font-bold text-slate-100 text-sm">
              Retrieval Quality on Paraphrased Questions (82 Questions, 11,540 Chunks)
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">Exact Sign Test: p = 0.004</span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
              <tr>
                <th className="px-4 py-3">Retriever Configuration</th>
                <th className="px-4 py-3">Setting</th>
                <th className="px-4 py-3">Recall@1</th>
                <th className="px-4 py-3">Recall@5</th>
                <th className="px-4 py-3">Recall@10</th>
                <th className="px-4 py-3">MRR@10</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/40">
              <tr className="hover:bg-slate-800/40">
                <td className="px-4 py-2.5 text-slate-300 font-sans font-medium">Dense Search Only (8B Embeddings)</td>
                <td className="px-4 py-2.5 text-slate-400">Open (No Filter)</td>
                <td className="px-4 py-2.5 text-slate-300">57.3%</td>
                <td className="px-4 py-2.5 text-slate-300">84.1%</td>
                <td className="px-4 py-2.5 text-slate-300">90.2%</td>
                <td className="px-4 py-2.5 text-slate-300">0.682</td>
              </tr>
              <tr className="hover:bg-slate-800/40 bg-emerald-950/20 font-semibold">
                <td className="px-4 py-2.5 text-emerald-300 font-sans">
                  Dense + Cross-Encoder Rerank (Production `ask`)
                </td>
                <td className="px-4 py-2.5 text-emerald-400">Open (No Filter)</td>
                <td className="px-4 py-2.5 text-emerald-300">84.1%</td>
                <td className="px-4 py-2.5 text-emerald-300">95.1%</td>
                <td className="px-4 py-2.5 text-emerald-300">96.3%</td>
                <td className="px-4 py-2.5 text-emerald-300">0.890</td>
              </tr>
              <tr className="hover:bg-slate-800/40">
                <td className="px-4 py-2.5 text-slate-300 font-sans font-medium">Dense Search Only (8B Embeddings)</td>
                <td className="px-4 py-2.5 text-slate-400">Scoped (Ticker + FY)</td>
                <td className="px-4 py-2.5 text-slate-300">61.0%</td>
                <td className="px-4 py-2.5 text-slate-300">90.2%</td>
                <td className="px-4 py-2.5 text-slate-300">96.3%</td>
                <td className="px-4 py-2.5 text-slate-300">0.727</td>
              </tr>
              <tr className="hover:bg-slate-800/40 bg-sky-950/20 font-semibold">
                <td className="px-4 py-2.5 text-sky-300 font-sans">
                  Dense + Cross-Encoder Rerank (Production `ask`)
                </td>
                <td className="px-4 py-2.5 text-sky-400">Scoped (Ticker + FY)</td>
                <td className="px-4 py-2.5 text-sky-300">86.6%</td>
                <td className="px-4 py-2.5 text-sky-300">98.8%</td>
                <td className="px-4 py-2.5 text-sky-300">100.0%</td>
                <td className="px-4 py-2.5 text-sky-300">0.920</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* The Wording Bias Insight */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <h3 className="font-mono font-bold text-slate-100 text-sm flex items-center gap-2">
          <ZapIcon className="w-4 h-4 text-amber-400" />
          <span>Key Discovery: The LLM Question Wording Bias & BM25 Mirage</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <span className="text-amber-400 font-bold block">1. Raw LLM-Generated Questions (Overlap = 0.67)</span>
            <p className="text-slate-400 font-sans text-xs leading-relaxed">
              When an LLM writes questions while reading a passage, it inadvertently copies exact vocabulary. BM25 keyword matching scored an impressive <strong>82.9% Recall@5</strong>, creating the false illusion of superior performance.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <span className="text-emerald-400 font-bold block">2. Paraphrased Questions (Overlap = 0.16)</span>
            <p className="text-slate-400 font-sans text-xs leading-relaxed">
              Rewriting the questions with realistic analyst vocabulary caused BM25 to collapse to <strong>22.0% Recall@5</strong>. Fusing BM25 with dense vectors via RRF lowered performance from 84.1% to 61.0%, leading to the decisive removal of BM25 from the pipeline.
            </p>
          </div>
        </div>
      </div>

      {/* SQL Analyst & Router Evaluation Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SQL Analyst */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <DatabaseIcon className="w-5 h-5 text-emerald-400" />
            <h3 className="font-mono font-bold text-slate-100 text-sm">SQL Analyst Execution Accuracy (46 Questions)</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-300">First-Run Execution Accuracy</span>
              <span className="font-mono font-bold text-emerald-400">93.5% (43 / 46)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-300">Out-of-Scope Questions Refused</span>
              <span className="font-mono font-bold text-emerald-400">100% (10 / 10)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-300">Tuned Accuracy After Prompt Calibrations</span>
              <span className="font-mono font-bold text-emerald-400">100% (46 / 46)</span>
            </div>
          </div>
        </div>

        {/* Router Evaluation */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <LayersIcon className="w-5 h-5 text-amber-400" />
            <h3 className="font-mono font-bold text-slate-100 text-sm">LangGraph Routing Precision (151 Questions)</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-300">Overall Routing Accuracy</span>
              <span className="font-mono font-bold text-emerald-400">94.0% (142 / 151)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-300">Hybrid Route Classification</span>
              <span className="font-mono font-bold text-emerald-400">100% (15 / 15)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-300">Answerable Questions Wrongly Refused</span>
              <span className="font-mono font-bold text-emerald-400">1 / 138 (MPLX Subsidiary)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
