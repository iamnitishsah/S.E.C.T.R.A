import React from 'react';
import {
  LayersIcon,
  DatabaseIcon,
  ShieldCheckIcon,
  ServerIcon,
  ZapIcon
} from '../components/common/Icons';

export const ArchitecturePage: React.FC = () => {
  return (
    <div className="space-y-10 pb-20">
      {/* Header */}
      <div className="space-y-2 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2">
          <LayersIcon className="w-5 h-5 text-emerald-400" />
          <h2 className="text-xl font-bold text-slate-100 font-mono">System Architecture & Safety Guardrails</h2>
        </div>
        <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
          S.E.C.T.R.A is engineered with multi-tiered defensive boundaries. No LLM ever accesses arbitrary database tables, executes raw SQL unchecked, or produces ungrounded citations.
        </p>
      </div>

      {/* Query Flow Diagram Card */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="font-mono font-bold text-slate-100 text-sm uppercase tracking-wider flex items-center gap-2">
            <ZapIcon className="w-4 h-4 text-emerald-400" />
            <span>Runtime Query Orchestration (LangGraph State Graph)</span>
          </h3>
          <span className="text-[11px] font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800">
            Conditional State Routing
          </span>
        </div>

        {/* Pipeline Step Boxes */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400 font-bold">1. Router Node</span>
              <span className="text-[10px] text-slate-500">LLM + Code</span>
            </div>
            <p className="text-slate-300 font-sans text-xs">
              Deconstructs query into classification (`sql`, `text`, `both`, `none`), extracts tickers and fiscal years.
            </p>
            <div className="text-[10px] text-slate-400 border-t border-slate-800/80 pt-1.5">
              Deterministic <code className="text-emerald-300">check_corpus()</code> catches unindexed companies.
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400 font-bold">2. SQL Node</span>
              <span className="text-[10px] text-slate-500">MySQL 8.4</span>
            </div>
            <p className="text-slate-300 font-sans text-xs">
              Generates single SELECT query. AST-validated by sqlglot. Executed by dedicated read-only database user.
            </p>
            <div className="text-[10px] text-slate-400 border-t border-slate-800/80 pt-1.5">
              Enforces 5s timeout & max 200 row limit.
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sky-400 font-bold">3. Text Node</span>
              <span className="text-[10px] text-slate-500">Qdrant + Rerank</span>
            </div>
            <p className="text-slate-300 font-sans text-xs">
              Dense vector search (top 60 candidates) followed by 8B cross-encoder reranker (top 5 passages).
            </p>
            <div className="text-[10px] text-slate-400 border-t border-slate-800/80 pt-1.5">
              Refusal score threshold: <code className="text-sky-300">0.042</code>.
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-amber-400 font-bold">4. Writer Node</span>
              <span className="text-[10px] text-slate-500">Synthesis & Audit</span>
            </div>
            <p className="text-slate-300 font-sans text-xs">
              Synthesizes answer citing <code className="text-emerald-300">[T]</code> for table and <code className="text-sky-300">[n]</code> for passages.
            </p>
            <div className="text-[10px] text-slate-400 border-t border-slate-800/80 pt-1.5">
              Automated regex fact & number verification check.
            </div>
          </div>
        </div>

        {/* Dynamic Scoping Highlight */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-300 flex items-start gap-3">
          <ZapIcon className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-amber-300">Dynamic Scoping Mechanism (Hybrid Execution):</span>
            <p className="text-slate-400 font-sans text-xs leading-relaxed">
              When a question does not name a specific company (e.g. <em>"Which healthcare company grew fastest in 2025 and why?"</em>), the SQL node executes first to identify the winning firm (<code className="text-slate-200">LLY</code>). The LangGraph state machine dynamically extracts that ticker and feeds it into the Text Node's filters, preventing multi-company noise from polluting retrieval.
            </p>
          </div>
        </div>
      </div>

      {/* Two-Layer SQL Safety */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <DatabaseIcon className="w-5 h-5 text-emerald-400" />
            <h3 className="font-mono font-bold text-slate-100 text-sm">Two-Layer SQL Safety Architecture</h3>
          </div>

          <div className="space-y-3 text-xs">
            {/* Layer 1 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
              <span className="font-mono text-emerald-400 font-bold block">Layer 1: Database Role Isolation</span>
              <p className="text-slate-400 leading-relaxed font-sans">
                A dedicated MySQL reader role (<code className="text-slate-200 font-mono">sectra_reader</code>) has strict <code className="text-emerald-300 font-mono">SELECT</code> permissions on only three tables: <code className="text-slate-200 font-mono">financial_metrics</code>, <code className="text-slate-200 font-mono">companies</code>, and <code className="text-slate-200 font-mono">filings</code>. Writes or reads of system tables fail at the engine level.
              </p>
            </div>

            {/* Layer 2 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
              <span className="font-mono text-emerald-400 font-bold block">Layer 2: AST Parser & Re-generation</span>
              <p className="text-slate-400 leading-relaxed font-sans">
                Queries are parsed via <code className="text-slate-200 font-mono">sqlglot</code>. Comments are completely stripped (blocking MySQL executable comments <code className="text-rose-400 font-mono">/*! ... */</code>), dangerous functions like <code className="text-slate-200 font-mono">SLEEP()</code> and <code className="text-slate-200 font-mono">BENCHMARK()</code> are rejected, and only queries re-generated from the verified parse tree execute.
              </p>
            </div>
          </div>
        </div>

        {/* Three-Tier Refusal Architecture */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheckIcon className="w-5 h-5 text-rose-400" />
            <h3 className="font-mono font-bold text-slate-100 text-sm">Three-Tier Refusal Architecture</h3>
          </div>

          <div className="space-y-3 text-xs">
            {/* Tier 1 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
              <span className="font-mono text-rose-400 font-bold block">Tier 1: Router & Deterministic Corpus Check</span>
              <p className="text-slate-400 leading-relaxed font-sans">
                Identifies unindexed companies, missing fiscal years, or advice requests before calling the embedding API or vector store. Stopped <strong>8 of 15</strong> unanswerable evaluation questions.
              </p>
            </div>

            {/* Tier 2 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
              <span className="font-mono text-amber-400 font-bold block">Tier 2: Retrieval Similarity Score Gate</span>
              <p className="text-slate-400 leading-relaxed font-sans">
                A score threshold (<code className="text-slate-200 font-mono">0.042</code> for cross-encoder reranking) drops weak semantic matches without calling the LLM writer. Stopped <strong>4 of 15</strong> unanswerable evaluation questions.
              </p>
            </div>

            {/* Tier 3 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
              <span className="font-mono text-sky-400 font-bold block">Tier 3: Writer Evidence Audit</span>
              <p className="text-slate-400 leading-relaxed font-sans">
                When passages look superficially related but don't substantiate the premise (e.g. fictitious acquisitions), the writer outputs <code className="text-slate-200 font-mono">NOT_FOUND</code>. Stopped <strong>3 of 15</strong> unanswerable evaluation questions.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Production AWS Deployment */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ServerIcon className="w-5 h-5 text-emerald-400" />
            <h3 className="font-mono font-bold text-slate-100 text-sm">Production AWS EC2 Deployment Topology</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">AWS EC2 (Ubuntu 24.04, t3.small)</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
            <span className="text-emerald-400 font-bold block">Isolated Loopback Ports</span>
            <p className="text-slate-400 font-sans text-xs leading-relaxed">
              MySQL 8.4 and Qdrant 1.18.2 are bound strictly to <code className="text-slate-200">127.0.0.1</code> inside Docker Compose. Only the FastAPI service (port 8000) is published externally.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
            <span className="text-sky-400 font-bold block">Zero-Drift CI/CD</span>
            <p className="text-slate-400 font-sans text-xs leading-relaxed">
              GitHub Actions triggers on push to <code className="text-slate-200">main</code>: executes 154 unit tests via pytest; on green, deploys via SSH with zero downtime.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
            <span className="text-amber-400 font-bold block">One-Way Data Sync</span>
            <p className="text-slate-400 font-sans text-xs leading-relaxed">
              The EC2 instance never downloads from SEC or runs heavy vector embeddings. Vectors and MySQL tables are loaded locally and migrated via SSH tunnel (<code className="text-slate-200">make deploy-data</code>).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
