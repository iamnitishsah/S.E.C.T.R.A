import React from 'react';
import {
  LayersIcon,
  DatabaseIcon,
  ShieldCheckIcon,
  ServerIcon,
  CheckIcon
} from '../components/common/Icons';

export const ArchitecturePage: React.FC = () => {
  return (
    <div className="space-y-10 pb-20">
      {/* Page Title */}
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
          <LayersIcon className="w-5 h-5 text-neutral-300" />
          <span>System Architecture & Safety Guardrails</span>
        </h2>
        <p className="text-xs text-neutral-400">
          Technical specifications of the offline pipeline, query runtime graph, AST SQL validator, and refusal boundaries.
        </p>
      </div>

      {/* Query Runtime Flow */}
      <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-tight">
            Query Execution Graph (LangGraph)
          </h3>
          <p className="text-xs text-neutral-400 mt-0.5">
            Incoming questions are routed conditionally through specialized nodes based on evidence requirements.
          </p>
        </div>

        {/* 4 Pipeline Step Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-white">1. Router Node</span>
              <span className="text-[10px] font-mono text-neutral-500">LLM + Catalog</span>
            </div>
            <p className="text-neutral-400 text-xs leading-relaxed">
              Deconstructs the question, assigns the route (<code className="font-mono text-neutral-300">sql | text | both | none</code>), and extracts companies and fiscal years.
            </p>
            <div className="text-[10px] text-neutral-500 font-mono pt-1 border-t border-neutral-800">
              Deterministic catalog check stops unindexed firms.
            </div>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-emerald-400">2. SQL Node</span>
              <span className="text-[10px] font-mono text-neutral-500">MySQL 8.4</span>
            </div>
            <p className="text-neutral-400 text-xs leading-relaxed">
              Generates a single SELECT statement. Validated against AST rules and executed with a read-only database user.
            </p>
            <div className="text-[10px] text-neutral-500 font-mono pt-1 border-t border-neutral-800">
              5-second query timeout & 200 row ceiling.
            </div>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-sky-400">3. Text Node</span>
              <span className="text-[10px] font-mono text-neutral-500">Qdrant + Rerank</span>
            </div>
            <p className="text-neutral-400 text-xs leading-relaxed">
              Dense vector search retrieves 60 candidates; an 8B cross-encoder API reranks them down to the top 5 passages.
            </p>
            <div className="text-[10px] text-neutral-500 font-mono pt-1 border-t border-neutral-800">
              Refusal score gate: min_score 0.042.
            </div>
          </div>

          <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-amber-400">4. Writer Node</span>
              <span className="text-[10px] font-mono text-neutral-500">Synthesis & Audit</span>
            </div>
            <p className="text-neutral-400 text-xs leading-relaxed">
              Synthesizes answers citing <code className="font-mono text-neutral-300">[T]</code> for table rows and <code className="font-mono text-neutral-300">[n]</code> for passages.
            </p>
            <div className="text-[10px] text-neutral-500 font-mono pt-1 border-t border-neutral-800">
              Verifies numbers and citations before reply.
            </div>
          </div>
        </div>

        {/* Dynamic Scoping Notice */}
        <div className="p-4 rounded-lg bg-[#0c0e12] border border-neutral-800 text-xs space-y-1">
          <span className="font-semibold text-neutral-200">
            Dynamic Scoping in Hybrid Execution:
          </span>
          <p className="text-neutral-400 leading-relaxed">
            When a query does not specify a company (e.g. <em>"Which healthcare company grew revenue fastest in 2025, and what drove that growth?"</em>), the SQL node executes first to identify the winning firm (<code className="font-mono text-neutral-300">LLY</code>). The graph then automatically scopes the text search to Eli Lilly and FY2025, eliminating cross-company noise.
          </p>
        </div>
      </div>

      {/* Two-Layer SQL Safety & Three-Tier Refusal */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SQL Safety */}
        <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <DatabaseIcon className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Two-Layer SQL Safety</h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
              <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
                <span>Layer 1: Dedicated Read-Only DB User</span>
              </div>
              <p className="text-neutral-400 leading-relaxed">
                The MySQL reader role (<code className="font-mono text-neutral-300">sectra_reader</code>) possesses strict SELECT privileges on only 3 tables: <code className="font-mono text-neutral-300">financial_metrics</code>, <code className="font-mono text-neutral-300">companies</code>, and <code className="font-mono text-neutral-300">filings</code>. Writes or reads of system tables are blocked at the engine level.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
              <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
                <span>Layer 2: AST Parser & Re-generation</span>
              </div>
              <p className="text-neutral-400 leading-relaxed">
                SQL queries are parsed with <code className="font-mono text-neutral-300">sqlglot</code>. Comments are completely stripped (defeating MySQL executable comments <code className="font-mono text-neutral-300">/*! ... */</code>), functions like <code className="font-mono text-neutral-300">SLEEP()</code> and <code className="font-mono text-neutral-300">BENCHMARK()</code> are rejected, and only re-generated AST queries are allowed to run.
              </p>
            </div>
          </div>
        </div>

        {/* Three-Tier Refusal */}
        <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheckIcon className="w-4 h-4 text-neutral-300" />
            <h3 className="text-sm font-semibold text-white">Three-Tier Refusal Architecture</h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
              <div className="font-semibold text-neutral-200">
                Tier 1: Router & Catalog Gate
              </div>
              <p className="text-neutral-400 leading-relaxed">
                Rejects unindexed tickers, missing fiscal years, or advice requests before any embedding or database queries run. (Refused 8 of 15 unanswerable benchmark questions).
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
              <div className="font-semibold text-neutral-200">
                Tier 2: Retrieval Score Gate
              </div>
              <p className="text-neutral-400 leading-relaxed">
                A calibrated threshold (<code className="font-mono text-neutral-300">0.042</code> for reranker) drops weak semantic matches without invoking the LLM generation backend. (Refused 4 of 15 benchmark questions).
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
              <div className="font-semibold text-neutral-200">
                Tier 3: Writer NOT_FOUND Rule
              </div>
              <p className="text-neutral-400 leading-relaxed">
                When passages appear superficially related but fail to substantiate the premise (such as fictitious mergers), the writer refuses to guess. (Refused 3 of 15 benchmark questions).
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Production Infrastructure */}
      <div className="border border-neutral-800 bg-[#101318] rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <ServerIcon className="w-4 h-4 text-neutral-300" />
          <h3 className="text-sm font-semibold text-white">Production Deployment Topology</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
            <span className="font-mono font-semibold text-neutral-200 block">AWS EC2 Hosting</span>
            <p className="text-neutral-400 leading-relaxed">
              FastAPI, MySQL 8.4, and Qdrant 1.18.2 run inside Docker Compose on Ubuntu Linux (t3.small).
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
            <span className="font-mono font-semibold text-neutral-200 block">Port Isolation</span>
            <p className="text-neutral-400 leading-relaxed">
              MySQL and Qdrant are bound strictly to <code className="font-mono text-neutral-300">127.0.0.1</code>. Only the FastAPI service (port 8000) is exposed.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-[#0c0e12] border border-neutral-800 space-y-1">
            <span className="font-mono font-semibold text-neutral-200 block">Automated CI/CD</span>
            <p className="text-neutral-400 leading-relaxed">
              GitHub Actions runs 154 unit tests via pytest on every push to <code className="font-mono text-neutral-300">main</code>, followed by automated SSH zero-downtime deployment.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
