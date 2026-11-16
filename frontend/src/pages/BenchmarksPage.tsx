import React from 'react';
import {
  BarChart3Icon,
  DatabaseIcon,
  FileTextIcon,
  LayersIcon
} from '../components/common/Icons';

export const BenchmarksPage: React.FC = () => {
  return (
    <div className="space-y-10 pb-20">
      {/* Header */}
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
          <BarChart3Icon className="w-5 h-5 text-neutral-300" />
          <span>Evaluation & Empirical Verification</span>
        </h2>
        <p className="text-xs text-neutral-400">
          Rigorous quantitative verification of retrieval recall, text-to-SQL execution accuracy, and unanswerable question refusal.
        </p>
      </div>

      {/* Summary KPI Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#101318] border border-neutral-800 space-y-1">
          <span className="text-xs font-mono text-neutral-500">Reranked Recall@5</span>
          <div className="text-2xl font-bold font-mono text-white">95.1%</div>
          <p className="text-[11px] text-neutral-400">82 paraphrased questions (Open search)</p>
        </div>

        <div className="p-4 rounded-xl bg-[#101318] border border-neutral-800 space-y-1">
          <span className="text-xs font-mono text-neutral-500">Scoped Recall@5</span>
          <div className="text-2xl font-bold font-mono text-white">98.8%</div>
          <p className="text-[11px] text-neutral-400">With router company/year filter</p>
        </div>

        <div className="p-4 rounded-xl bg-[#101318] border border-neutral-800 space-y-1">
          <span className="text-xs font-mono text-neutral-500">Text-to-SQL Accuracy</span>
          <div className="text-2xl font-bold font-mono text-white">93.5%</div>
          <p className="text-[11px] text-neutral-400">43 / 46 on first run (46/46 tuned)</p>
        </div>

        <div className="p-4 rounded-xl bg-[#101318] border border-neutral-800 space-y-1">
          <span className="text-xs font-mono text-neutral-500">Refusal of Unanswerable</span>
          <div className="text-2xl font-bold font-mono text-white">15 / 15</div>
          <p className="text-[11px] text-neutral-400">100% end-to-end refusal</p>
        </div>
      </div>

      {/* Retrieval Evaluation Table */}
      <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileTextIcon className="w-4 h-4 text-neutral-300" />
            <h3 className="text-sm font-semibold text-white">
              Retrieval Quality on Paraphrased Questions (82 Questions across 11,540 Chunks)
            </h3>
          </div>
          <span className="text-xs font-mono text-neutral-500">Sign Test: p = 0.004</span>
        </div>

        <div className="overflow-x-auto rounded-lg border border-neutral-800">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0c0e12] text-neutral-400 border-b border-neutral-800 uppercase text-[10px]">
              <tr>
                <th className="px-4 py-3 font-medium">Retriever Configuration</th>
                <th className="px-4 py-3 font-medium">Setting</th>
                <th className="px-4 py-3 font-medium">Recall@1</th>
                <th className="px-4 py-3 font-medium">Recall@5</th>
                <th className="px-4 py-3 font-medium">Recall@10</th>
                <th className="px-4 py-3 font-medium">MRR@10</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60 bg-[#101318]">
              <tr className="hover:bg-neutral-800/30">
                <td className="px-4 py-2.5 text-neutral-300 font-sans">Dense Vector Search (8B Embeddings)</td>
                <td className="px-4 py-2.5 text-neutral-400">Open (No Filter)</td>
                <td className="px-4 py-2.5 text-neutral-300">57.3%</td>
                <td className="px-4 py-2.5 text-neutral-300">84.1%</td>
                <td className="px-4 py-2.5 text-neutral-300">90.2%</td>
                <td className="px-4 py-2.5 text-neutral-300">0.682</td>
              </tr>
              <tr className="hover:bg-neutral-800/30 bg-neutral-900/60 font-semibold">
                <td className="px-4 py-2.5 text-white font-sans">
                  Dense + Cross-Encoder Rerank (Production `ask`)
                </td>
                <td className="px-4 py-2.5 text-neutral-300">Open (No Filter)</td>
                <td className="px-4 py-2.5 text-white">84.1%</td>
                <td className="px-4 py-2.5 text-white font-bold">95.1%</td>
                <td className="px-4 py-2.5 text-white">96.3%</td>
                <td className="px-4 py-2.5 text-white">0.890</td>
              </tr>
              <tr className="hover:bg-neutral-800/30">
                <td className="px-4 py-2.5 text-neutral-300 font-sans">Dense Vector Search (8B Embeddings)</td>
                <td className="px-4 py-2.5 text-neutral-400">Scoped (Ticker + FY)</td>
                <td className="px-4 py-2.5 text-neutral-300">61.0%</td>
                <td className="px-4 py-2.5 text-neutral-300">90.2%</td>
                <td className="px-4 py-2.5 text-neutral-300">96.3%</td>
                <td className="px-4 py-2.5 text-neutral-300">0.727</td>
              </tr>
              <tr className="hover:bg-neutral-800/30 bg-neutral-900/60 font-semibold">
                <td className="px-4 py-2.5 text-white font-sans">
                  Dense + Cross-Encoder Rerank (Production `ask`)
                </td>
                <td className="px-4 py-2.5 text-neutral-300">Scoped (Ticker + FY)</td>
                <td className="px-4 py-2.5 text-white">86.6%</td>
                <td className="px-4 py-2.5 text-white font-bold">98.8%</td>
                <td className="px-4 py-2.5 text-white">100.0%</td>
                <td className="px-4 py-2.5 text-white">0.920</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* The Wording Bias Insight */}
      <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white">
          Key Discovery: LLM Wording Bias and BM25 Elimination
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <span className="font-semibold text-neutral-200 block">
              1. Raw LLM-Written Questions (Word Overlap: 0.67)
            </span>
            <p className="text-neutral-400 leading-relaxed font-sans">
              When an LLM writes questions while viewing a passage, it reuses the passage's vocabulary. Keyword matching (BM25) scored <strong>82.9% Recall@5</strong>, creating a misleading impression of effectiveness.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <span className="font-semibold text-neutral-200 block">
              2. Paraphrased Questions (Word Overlap: 0.16)
            </span>
            <p className="text-neutral-400 leading-relaxed font-sans">
              Rewriting questions with realistic financial terminology caused BM25 to collapse to <strong>22.0% Recall@5</strong>. Fusing BM25 with dense vectors via RRF lowered accuracy from 84.1% to 61.0%, so BM25 was removed.
            </p>
          </div>
        </div>
      </div>

      {/* SQL Analyst & Router Accuracy Tables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SQL Analyst */}
        <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <DatabaseIcon className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Text-to-SQL Execution Accuracy</h3>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0c0e12] border border-neutral-800">
              <span className="text-neutral-300">First-Run Execution Accuracy</span>
              <span className="font-mono font-semibold text-white">93.5% (43 / 46)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0c0e12] border border-neutral-800">
              <span className="text-neutral-300">Out-of-Scope Questions Refused</span>
              <span className="font-mono font-semibold text-white">100% (10 / 10)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0c0e12] border border-neutral-800">
              <span className="text-neutral-300">Tuned Accuracy After Fixes</span>
              <span className="font-mono font-semibold text-white">100% (46 / 46)</span>
            </div>
          </div>
        </div>

        {/* Router Evaluation */}
        <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <LayersIcon className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">LangGraph Router Precision</h3>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0c0e12] border border-neutral-800">
              <span className="text-neutral-300">Overall Routing Accuracy</span>
              <span className="font-mono font-semibold text-white">94.0% (142 / 151)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0c0e12] border border-neutral-800">
              <span className="text-neutral-300">Hybrid Route Classification</span>
              <span className="font-mono font-semibold text-white">100% (15 / 15)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0c0e12] border border-neutral-800">
              <span className="text-neutral-300">Answerable Questions Wrongly Refused</span>
              <span className="font-mono font-semibold text-white">1 / 138 (MPLX subsidiary)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
