# S.E.C.T.R.A Web Client

A domain-aligned, minimal, institutional financial terminal interface for **S.E.C.T.R.A** (*Securities & Exchange Commission Tracking, Retrieval & Analysis*). Connects to the exposed FastAPI service on AWS EC2 or a local instance.

---

## Features

- **Institutional Design**: Slate/zinc palette with monospace numeric precision, Bloomberg/FactSet quantitative research aesthetic.
- **Tripartite Routing & Trace Visualization**: Step-by-step LangGraph orchestration trace (`router` → `sql` → `text` → `writer`) with route status badges (`SQL`, `TEXT`, `HYBRID`, `REFUSED`).
- **Interactive Citations**: Clickable `[T]` indicators scroll to the executed SQL table; `[n]` indicators highlight source 10-K passages with direct links to SEC EDGAR archive filings.
- **Factuality & Citation Guardrails**: Real-time warnings for uncited statements, unsupported figures, or token limits.
- **Dynamic Endpoint Configuration**: Live backend health badge with ping latency indicator and in-app switcher between AWS EC2 (`http://32.236.49.234:8000`) and Localhost (`http://localhost:8000`).

---

## 4 Dedicated Views

1. **Overview & Data Engine (`/overview`)**: Executive problem statement, the 3-pillar source of truth model, dataset scope (20 companies, 80 filings, 534k facts, 11.5k chunks), XBRL normalization rules, and interactive sector-filtered company catalog.
2. **Research Terminal (`/demo`)**: Preset query benchmarks across numeric, narrative, hybrid, and unanswerable categories; live query submission; grounded answers; structured SQL data table inspector; and retrieved passage cards.
3. **Architecture & Safety (`/architecture`)**: Offline ingestion pipeline, query-time LangGraph orchestration with dynamic scoping, two-layer SQL safety (read-only user + `sqlglot` AST validator), and three-tier refusal architecture.
4. **Benchmarks & Eval (`/benchmarks`)**: Empirical retrieval accuracy (95.1% Reranked Recall@5, 98.8% scoped), wording bias experiment (BM25 82.9% on raw vs 22.0% on paraphrased), and 93.5% first-run text-to-SQL accuracy.

---

## Configuration (`.env`)

The web client reads from `frontend/.env` (or in-app settings modal stored in `localStorage`):

```bash
# AWS EC2 FastAPI Endpoint
VITE_API_BASE_URL=http://32.236.49.234:8000

# Authentication Header
VITE_API_KEY=SECTRA@Nitish
```

---

## Running Locally

```bash
# From repository root:
make frontend

# Or from inside frontend/:
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Production Build

```bash
cd frontend
npm run build
npm run preview
```
