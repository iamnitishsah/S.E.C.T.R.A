# **S.E.C.T.R.A**
###### *Securities & Exchange Commission Tracking, Retrieval & Analysis*

**A research system over SEC EDGAR 10-K filings. Numeric questions are answered from a validated financial database, textual questions with cited retrieval-augmented generation (RAG), and hybrid questions with both. Every claim traces to a source.**

| | |
|---|---|
| Corpus | 20 companies, 80 annual reports, 534,026 XBRL facts, 11,540 text chunks |
| Retrieval | **95.1% Recall@5** on 82 paraphrased questions searched across the whole corpus (84.1% before reranking) |
| Text-to-SQL | **93.5%** execution accuracy on 46 questions on the first run |
| Routing | **94.0%** of 151 questions routed correctly; **15 of 15** unanswerable questions refused end to end |
| Deployment | FastAPI service on AWS EC2 with Docker Compose; GitHub Actions tests and deploys every push to `main` |
| Status | Pipeline, SQL Analyst, research graph, API and deployment complete · answer faithfulness and a web frontend planned |

---

## Contents

1. [Overview](#1-overview)
2. [Results](#2-results)
3. [Architecture](#3-architecture)
4. [Documentation](#4-documentation)
5. [Running the project](#5-running-the-project)
6. [API and deployment](#6-api-and-deployment)
7. [Roadmap](#7-roadmap)
8. [Repository structure](#8-repository-structure)
9. [Tech stack](#9-tech-stack)
10. [Limitations](#10-limitations)

---

## 1. Overview

### The problem

Analysts spend much of their time on two tasks:

- **Searching long filings** (often 100+ pages) for a specific risk, policy, or explanation.
- **Connecting numbers to narrative**: *"Revenue grew 30%, but what did management say drove it?"*

A general-purpose chatbot handles both poorly. It can invent figures, it does arithmetic unreliably, and it cannot point to the exact filing section a claim came from.

### The approach

S.E.C.T.R.A gives each kind of question to the tool that is good at it:

| Need | Source of truth | Mechanism | Status |
|---|---|---|---|
| Exact figures (revenue, net income, assets…) | XBRL facts in **MySQL**, normalized into 15 canonical metrics | Text-to-SQL agent over `financial_metrics`, validated and read-only | ✅ built and measured |
| Explanations, risks, strategy | Filing text in **Qdrant**, split by 10-K Item | Dense retrieval → reranking → cited generation | ✅ built and measured |
| Questions needing both | Both | LangGraph: router → SQL → retrieval → one writer citing table and passages | ✅ built and measured |

**Design principle: the LLM never supplies facts from memory.** Every figure must come from a database row and every textual claim from a retrieved passage. When the evidence is missing, the system says *"not found"* instead of guessing.

### Example

```text
$ python -m sectra.rag.ask "What export restrictions affect NVIDIA's sales to China?" --ticker NVDA --year 2025
[backend: groq / openai/gpt-oss-120b | retriever: rerank, min_score 0.042]

In its FY 2025 10-K NVIDIA explains that U.S. export-control rules now require licenses for virtually
all of its high-performance products shipped to China (including Hong Kong and Macau).

* August 2022 – the U.S. government announced licensing requirements for exports of the A100 and H100
  integrated circuits, DGX systems or any boards that incorporate those chips to China and Russia [2].
* July 2023 – an additional licensing requirement was added for a subset of A100 and H100 products
  destined for certain customers and other regions, including some Middle-East countries [1][2][4].
  ...

Sources:
 *[1] NVDA 10-K FY2025 | Item 1A Risk Factors | Risks Related to Regulatory, Legal, Our Stock and Other Matters  (score 0.179)
       0001045810-25-000023_1A_049  https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm
 *[2] NVDA 10-K FY2025 | Item 1 Business | Government Regulations  (score 0.142)
       0001045810-25-000023_1_023  https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm
  ...
[openai/gpt-oss-120b | 1768 in / 817 out tokens | 2.6s]

$ python -m sectra.rag.ask "What is Tesla's battery supply strategy?"
Not found in the indexed filings.
(reason: best match too weak (score 0.04 < 0.042))
```

`*` marks passages the answer actually cites. Each citation resolves to a chunk ID, an accession number, a 10-K Item, and the SEC URL of the original document. Tesla is not in the corpus, so the second question is refused before any LLM call.

---

## 2. Results

### Pipeline

| Component | Measure | Result |
|---|---|---|
| Data acquisition | 10-K filings downloaded and verified (SHA-256) | **80 / 80** |
| XBRL load | Fact rows loaded vs. source count | **534,026 / 534,026** |
| Fiscal-year derivation | Downloaded filings labelled | **80 / 80**; SEC's own `fy` field was wrong for 4 NVIDIA filings |
| Metric normalization | FY2025 coverage of core metrics (revenue, net income, EPS, assets, equity, operating cash flow) | **20 / 20 companies** |
| Metric validation | Values compared by hand with printed statements | **10 / 10 match** after one mapping fix (Chevron revenue) |
| Section extraction | Filings with Items 1A **and** 7 correctly extracted | **76 / 80 (95.0%)**; all 4 failures have one known cause |
| Chunking | Chunks produced | **11,540** (median 319 tokens, max 458) |
| Tests | Unit tests, no network | **154 passing** |

### Retrieval

82 answerable questions, worded differently from the passage that answers them, searched across all 11,540 chunks with no filters:

| Retriever | Recall@1 | Recall@5 | MRR@10 |
|---|---|---|---|
| Dense search | 57.3% | 84.1% | 0.682 |
| **Dense search + reranking** | **84.1%** | **95.1%** | **0.890** |

With the company and fiscal year given as filters, reranked Recall@5 is 98.8%.

What was learned on the way, with the full numbers in [docs/05-evaluation.md](docs/05-evaluation.md):

- **The embedding model was the bottleneck.** Replacing a small local model with a hosted 8B model raised dense Recall@5 from 24.4% to 84.1%.
- **Keyword search looked best until the questions were paraphrased.** BM25 scored 82.9% on LLM-written questions that reused the passage's wording and 22.0% on paraphrases of the same questions.
- **Hybrid search stopped helping.** Fusing BM25 with the stronger dense ranking lowered Recall@5 from 84.1% to 61.0%, so BM25 was removed.
- **A similarity score is a weak refusal signal.** A threshold that refuses no real question stops 5 of 15 unanswerable ones; the rest are left to the model's `NOT_FOUND` rule.

Not measured yet: whether generated answers are supported by the passages they cite.

### SQL Analyst

46 questions with gold SQL, scored by comparing query results (execution accuracy):

| Run | Accuracy |
|---|---|
| First run | 43 / 46 (**93.5%**), after correcting one flawed gold query |

No query needed a retry, and all 10 questions the database cannot answer (unreported metrics, stock prices, forecasts, companies that are not indexed) were declined or returned no rows. A wrong ticker guess, a missing year filter and an ignored default year were the three real failures; details are in [docs/06-sql-analyst.md](docs/06-sql-analyst.md).

```text
$ python -m sectra.analyst.agent "Which semiconductor company had the highest net income in fiscal 2025?"
The semiconductor company with the highest net income in fiscal 2025 is NVIDIA, with 72.88 bn.

ticker  fiscal_year  source_accession      net_income_bn
NVDA    2025         0001045810-26-000021  72.88
```

### Research graph

One command routes a question to the database, the filing text, or both (158 questions with known handling):

| Measure | Result |
|---|---|
| Routed correctly | 142 / 151 (**94.0%**); hybrid 15 / 15, narrative 79 / 82, numeric 40 / 46 |
| Answerable questions wrongly refused | 1 / 138 |
| Company and fiscal year extracted | 94 / 94 and 81 / 81 |
| Recall@5 using the router's filters | **98.8%**, equal to perfect filters (95.1% with none) |
| Unanswerable questions refused end to end | **15 / 15** (the retrieval-score gate alone: 5 / 15) |

The 15 refusals came from three layers: the router and corpus check (8), the evidence check (4) and the writer (3). Details and failures are in [docs/07-research-graph.md](docs/07-research-graph.md).

```text
$ python -m sectra.agents.graph "Which healthcare company grew revenue fastest in fiscal 2025, and what drove that growth?"
Eli Lilly grew revenue fastest, at 44.7 % year-over-year in fiscal 2025 [T]. Revenue rose mainly because
volume increased sharply, especially for Mounjaro and Zepbound [1][2].

Steps:  router: both  ->  sql: 1 rows  ->  text: 5 passages (LLY FY2025)  ->  writer
```

(Output abridged.) The question names no company: the SQL step finds it, and the text search is then filtered to that company and year.

---

## 3. Architecture

Solid boxes are built; dashed boxes are planned.

```mermaid
flowchart TB
    subgraph SRC["SEC EDGAR"]
        S1["Submissions API<br/>company metadata + filing index"]
        S2["Company Facts API<br/>XBRL facts, all filings"]
        S3["10-K documents<br/>inline XBRL HTML"]
    end

    subgraph ING["Offline pipeline: make all"]
        I1["EDGAR client<br/>rate limit, retry, cache"]
        I2["XBRL loader<br/>fiscal years, dedup, metric map"]
        I3["HTML to text<br/>Item splitter"]
        I4["Chunker"]
        I5["Embedding API<br/>cached, resumable"]
    end

    subgraph STORE["Storage"]
        D1[("MySQL 8.4<br/>facts, metrics, sections")]
        D2[("Qdrant 1.18<br/>11,540 vectors, 1,024-d")]
    end

    subgraph QRY["Query layer"]
        Q1["CLI: sectra.rag.ask"]
        Q2["Dense retrieval<br/>filter by ticker, year, Item"]
        Q4["Rerank API<br/>60 candidates to 5"]
        Q3["Answer generator<br/>cited, refuses on weak evidence"]
        L1["LLM API<br/>Groq, Gemini or NVIDIA"]
        Q5["CLI: sectra.analyst.agent"]
        Q6["SQL Analyst<br/>text-to-SQL, validator,<br/>read-only user"]
        Q7["CLI: sectra.agents.graph"]
        Q8["Research graph (LangGraph)<br/>router, corpus check, writer"]
        Q9["FastAPI service<br/>/ask, /companies, /health"]
        P3["Web frontend"]
    end

    S1 --> I1
    S2 --> I1
    S3 --> I1
    I1 --> I2 --> D1
    I1 --> I3 --> D1
    I3 --> I4 --> I5 --> D2
    Q1 --> Q2 --> D2
    Q2 --> Q4 --> Q3
    Q3 --> L1
    Q5 --> Q6 --> D1
    Q6 --> L1
    Q7 --> Q8
    Q8 --> Q6
    Q8 --> Q2
    Q8 --> L1
    Q9 --> Q8
    P3 -.-> Q9

    classDef planned stroke-dasharray: 5 5,color:#888
    class P3 planned
```

Every model (embedding, reranking, generation) is reached through a hosted API and chosen in `configs/`; no model name appears in the code. The step-by-step query flow is in [docs/04-retrieval-and-answers.md](docs/04-retrieval-and-answers.md).

### Offline pipeline

Every stage is idempotent: re-running it produces the same result without duplicates.

```mermaid
flowchart LR
    A["configs/companies.yaml"] --> B["download<br/>ticker to CIK, filing index,<br/>10-K HTML, companyfacts"]
    B --> M["manifests<br/>companies.csv, filings.csv"]
    M --> C["db<br/>schema, load facts,<br/>derive views, materialize metrics"]
    B --> D["sections<br/>HTML to text to Items"]
    C --> D
    D --> E["chunks<br/>~350-token chunks"]
    E --> F["embed<br/>API vectors, cached"]
    F --> G["index<br/>Qdrant collection"]
```

| `make` target | What it does | Typical time |
|---|---|---|
| `up` / `down` | Start or stop MySQL and Qdrant | |
| `download` | Fetch filing indexes, 10-K documents and XBRL (cached), write manifests and `docs/dataset.md` | ~70 s cold, ~1 s cached |
| `db` | `db-schema` → `db-load` (manifests, 534K facts, metric map) → `db-derive` (views, materialized metrics) → `db-role` (read-only user) | ~45 s |
| `sections` | Split all 80 filings into Items, write files + `filing_sections` + parse report | ~15 s |
| `chunks` | Section-aware chunking → `chunks.jsonl` | ~30 s |
| `embed` | Embed new or changed chunks through the embedding API | ~20 min first run, seconds after |
| `index` | Upsert into Qdrant, delete stale points | ~20 s |
| `all` | Everything above from `download` to `index` | |
| `test` | Unit tests | <1 s |
| `eval` | Retrieval evaluation on both question sets | a few minutes |
| `threshold` | Refusal-threshold sweep from the saved results | <1 s |
| `sql-eval` | SQL Analyst evaluation on 46 questions | ~8 min |
| `routing-eval` | Router, routed retrieval and end-to-end refusal on 158 questions | ~12 min |
| `api` | Run the API locally with reload | |
| `build` / `up-api` / `logs` | Build the API image, run it next to MySQL and Qdrant, follow its logs | |
| `deploy-data HOST=user@host` | Copy this machine's database and vectors to a server | ~3 min |

---

## 4. Documentation

| Document | Contents |
|---|---|
| [docs/01-data-acquisition.md](docs/01-data-acquisition.md) | SEC, EDGAR and XBRL background; dataset scope; the download client; on-disk layout |
| [docs/02-financial-database.md](docs/02-financial-database.md) | Why raw XBRL cannot be queried directly; schema; fiscal-year derivation; the metric map; validation |
| [docs/03-filing-text.md](docs/03-filing-text.md) | HTML to clean text; splitting a 10-K into Items; chunking rules |
| [docs/04-retrieval-and-answers.md](docs/04-retrieval-and-answers.md) | Embeddings, vector store, reranking, LLM layer, citation checks, the two refusal layers |
| [docs/05-evaluation.md](docs/05-evaluation.md) | How the question sets were built; every retrieval variant measured; threshold calibration; what the numbers do not show |
| [docs/07-research-graph.md](docs/07-research-graph.md) | The LangGraph graph: router, corpus check, nodes, the writer and its checks; routing, routed-retrieval and refusal evaluation |
| [docs/06-sql-analyst.md](docs/06-sql-analyst.md) | Text-to-SQL flow; the read-only user and the query validator; the number check; execution-accuracy evaluation and its failures |
| [docs/findings.md](docs/findings.md) | Problems found in the data and the pipeline, with evidence and fixes; changes to the original plan |
| [eval/results/experiments.md](eval/results/experiments.md) | Archived numbers for every retrieval experiment, including removed variants |

---

## 5. Running the project

### Prerequisites

Python 3.11+, Docker, ~1 GB free disk, an SEC-compliant `User-Agent`, and API keys for the embedding/reranking provider and at least one LLM provider. Developed on an 8 GB Apple-Silicon Mac; no model runs locally.

### Setup

```bash
git clone https://github.com/iamnitishsah/S.E.C.T.R.A.git
cd S.E.C.T.R.A
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # fill in the values below
make up                       # MySQL 8.4 + Qdrant 1.18.2
make all                      # download -> db -> sections -> chunks -> embed -> index
make test
```

The first `make all` downloads ~313 MB from SEC and embeds 11,540 chunks through the embedding API (about 20 minutes on a free endpoint; it checkpoints and resumes if interrupted). Every later run is incremental.

### Configuration

**`.env`**

| Variable | Purpose |
|---|---|
| `SEC_USER_AGENT` | `"Your Name you@email.com"`, required by SEC |
| `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT` | Database |
| `MYSQL_READER_USER`, `MYSQL_READER_PASSWORD` | Read-only database user for generated SQL (created by `make db-role`) |
| `QDRANT_URL` | `http://localhost:6333` |
| `NVIDIA_API_KEY` | Embedding and reranking APIs (and the `nvidia` LLM backend) |
| `GROQ_API_KEY`, `GEMINI_API_KEY` | LLM providers |
| `LLM_BACKEND` | `groq`, `gemini` or `nvidia` |
| `SECTRA_API_KEY` | If set, `POST /ask` requires the header `X-API-Key` |
| `CORS_ORIGINS` | Browser origins allowed to call the API, comma-separated |
| `RATE_LIMIT_PER_MIN` | Requests per minute per client IP on `/ask` (default 20) |

**`configs/`**

| File | Contents |
|---|---|
| `companies.yaml` | Tickers by sector; forms; filings per company |
| `retrieval.yaml` | Indexed Items; chunking; embedding API (URL, model, key variable, dimensions); vector store; rerank API and candidate count; which retriever `ask` uses and its refusal threshold |
| `sql.yaml` | SQL Analyst: table allowlist, row limit, query timeout, read-only user variables |
| `agents.yaml` | Company-name aliases for the router |
| `llm.yaml` | LLM backends (base URL, key variable, model); generation settings (`temperature: 0`, `max_tokens: 2000`) |

Switching a model or provider is a config change. Changing the embedding model or its dimensions requires `make embed index`, and the refusal thresholds should be recalibrated with `make eval threshold`.

### Usage

```bash
# Ask the filings
python -m sectra.rag.ask "What does NVIDIA say drove its data center revenue growth?" --ticker NVDA --year 2026 --item 7
python -m sectra.rag.ask "..." --backend gemini --show-passages
python -m sectra.rag.ask "..." --retriever dense          # skip reranking
python -m sectra.llm.base groq                            # list models available to your key

# Ask the financial database
python -m sectra.analyst.agent "Which companies grew revenue by more than 20% in fiscal 2025?" --show-sql
python -m sectra.analyst.tools                            # the schema text the model sees

# Ask anything: routed to the database, the filings, or both
python -m sectra.agents.graph "How fast did Nvidia's revenue grow in fiscal 2025, and what drove it?" --show-sql
python -m sectra.agents.router "..."                       # the routing decision only

# Measure
make eval                                                 # retrieval
make threshold
make sql-eval                                             # SQL Analyst
make routing-eval                                         # router, routed retrieval, refusal

# Query the financial database by hand (MySQL shell)
docker compose exec mysql sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"'
```
```sql
SELECT fiscal_year, ROUND(value / 1e9, 2) AS net_income_bn, source_accession
FROM financial_metrics
WHERE ticker = 'NVDA' AND canonical_metric = 'net_income'
ORDER BY fiscal_year DESC LIMIT 5;
```

The Qdrant dashboard is at http://localhost:6333/dashboard.

---

## 6. API and deployment

### API (`src/sectra/api/main.py`)

A FastAPI service over the research graph. The graph, the retriever, the company catalog and the database connections are built once at startup and reused by every request.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Whether the service is up, and what is loaded |
| `GET /companies` | The indexed companies, with the fiscal years that have filing text and metrics |
| `POST /ask` | `{"question": "..."}` → the answer, its evidence, checks and a step trace |
| `GET /docs` | Interactive OpenAPI documentation, generated from the typed request and response models |

```bash
make api                                   # http://localhost:8000/docs
curl -s -X POST localhost:8000/ask -H "Content-Type: application/json" -H "X-API-Key: $SECTRA_API_KEY" \
  -d '{"question": "Which semiconductor company had the highest net income in fiscal 2025?"}'
```

```json
{
  "question": "Which semiconductor company had the highest net income in fiscal 2025?",
  "answer": "NVIDIA reported the highest net income among semiconductor companies in fiscal 2025, with $72.88 billion [T].",
  "route": "sql",
  "answered": true,
  "table": {
    "sql": "SELECT fm.ticker, fm.fiscal_year, fm.source_accession, ROUND(fm.value / 1e9, 2) AS net_income_bn FROM ...",
    "columns": ["ticker", "fiscal_year", "source_accession", "net_income_bn"],
    "rows": [["NVDA", 2025, "0001045810-26-000021", 72.88]],
    "source_filings": ["0001045810-26-000021"]
  },
  "passages": [],
  "warnings": {},
  "steps": ["router: sql", "sql: 1 rows", "writer: answer written, 0 kind(s) of warning"]
}
```

(Response abridged; it also carries the model, token counts and latency.)

- **A declined question is a normal response**: HTTP 200 with `"answered": false` and a `reason`. Only a real failure, such as an LLM or database error, returns 502.
- **Passages carry a `cited` flag**, so a client can show which sources the answer used.
- **An API key and a per-IP rate limit** protect the LLM quota behind a public endpoint. CORS origins are set in `.env`.

### Deployment

One AWS EC2 instance (Ubuntu, `t3.small`) runs the same `docker-compose.yml` as a development machine. Only `.env` differs.

```mermaid
flowchart LR
    DEV["Developer machine<br/>loaded MySQL + cached vectors"]
    GH["GitHub<br/>push to main"]
    CI["GitHub Actions<br/>pytest, then deploy over SSH"]
    U["Client"]

    subgraph EC2["EC2 instance: docker compose"]
        API["api :8000<br/>FastAPI + research graph"]
        MY[("mysql<br/>127.0.0.1 only")]
        QD[("qdrant<br/>127.0.0.1 only")]
    end
    EXT["LLM, embedding and<br/>rerank APIs"]

    U -->|"HTTP + X-API-Key"| API
    API --> MY
    API --> QD
    API --> EXT
    GH --> CI -->|"git pull, rebuild api"| API
    DEV -.->|"make deploy-data (once)"| MY
    DEV -.->|"SSH tunnel (once)"| QD
```

| Choice | Reason |
|---|---|
| One Compose file for laptop and server | No drift between environments; the same `make up`, `make build`, `make up-api`, `make logs` work on both |
| MySQL and Qdrant bound to `127.0.0.1` | Neither database is reachable from the network, whatever the firewall allows. Only the API port is published |
| Data copied from the development machine | The server never downloads from SEC or calls the embedding API. `scripts/deploy_data.sh` restores a dump of the local database over SSH, creates the read-only user, and indexes the cached vectors through an SSH tunnel, then prints row counts from both sides |
| API image built on the server | No registry to manage; the image matches the instance's architecture |
| `.env` copied with `scp` | Secrets never pass through git or GitHub |

First-time setup, from the development machine:

```bash
export HOST=ubuntu@<public-ip>
ssh -i ~/.ssh/<key>.pem $HOST 'bash -s' < scripts/server_setup.sh        # Docker, git, make, 2 GB swap
ssh -i ~/.ssh/<key>.pem $HOST 'git clone https://github.com/iamnitishsah/S.E.C.T.R.A.git && mkdir -p S.E.C.T.R.A/data/logs'
scp -i ~/.ssh/<key>.pem .env $HOST:S.E.C.T.R.A/.env
ssh -i ~/.ssh/<key>.pem $HOST 'cd S.E.C.T.R.A && make up && make build'
make deploy-data HOST=$HOST                                              # database + vectors
ssh -i ~/.ssh/<key>.pem $HOST 'cd S.E.C.T.R.A && make up-api'
curl -s -m 10 http://<public-ip>:8000/health
```

The instance's security group allows SSH (22) and the API port (8000).

### CI/CD (`.github/workflows/deploy.yml`)

Every push to `main` runs two jobs:

1. **test**: install the project and run the unit tests.
2. **deploy**: only if the tests pass, connect to the instance over SSH, `git pull`, rebuild and restart the API container, and wait for `/health` to answer. The databases are not touched.

It needs three repository secrets: `EC2_HOST`, `EC2_USER` and `EC2_SSH_KEY`.

---

## 7. Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0–1 | Data acquisition; XBRL → MySQL; fiscal years; canonical metrics; validation | ✅ |
| 2 | 10-K HTML → clean text → Items | ✅ |
| 3 | Chunking, embeddings, vector store, cited answers with refusal | ✅ |
| 4 | Evaluation and retrieval upgrades | Retrieval and refusal threshold ✅ · answer faithfulness and generator comparison pending |
| 5 | SQL Analyst: text-to-SQL with a query validator and a read-only user; execution-accuracy evaluation | ✅ |
| 6 | Research graph (LangGraph): router, corpus check, SQL and text nodes, one cited writer; routing evaluation | ✅ |
| 7 | Risk diffing between two fiscal years of Item 1A | Skipped |
| 8 | FastAPI service, Docker image, AWS EC2 deployment, GitHub Actions CI/CD | ✅ |
| 9 | Web frontend, HTTPS, injection filter and red-team set, failure analysis | Planned |

---

## 8. Repository structure

```text
S.E.C.T.R.A/
├── README.md
├── Makefile                     # make = help; pipeline, evaluation, API and deploy targets
├── docker-compose.yml           # MySQL 8.4, Qdrant 1.18.2, API (same file locally and on the server)
├── Dockerfile                   # API image
├── .github/workflows/deploy.yml # test, then deploy to EC2 on push to main
├── scripts/
│   ├── server_setup.sh          # one-time server setup: Docker, git, make, swap
│   └── deploy_data.sh           # copy the local database and vectors to the server
├── pyproject.toml
├── .env.example
│
├── configs/
│   ├── companies.yaml           # tickers by sector, forms, filings per company
│   ├── retrieval.yaml           # chunking, embedding API, vector store, rerank API, answering
│   ├── sql.yaml                 # SQL Analyst: table allowlist, row limit, timeout
│   ├── agents.yaml              # company-name aliases for the router
│   └── llm.yaml                 # LLM backends and generation settings
│
├── sql/
│   ├── schema.sql               # tables
│   ├── views.sql                # fiscal years, annual facts, metric view
│   ├── post_load.sql            # filings.fiscal_year + materialized financial_metrics
│   └── metric_map.csv           # XBRL tag -> canonical metric (priorities, overrides)
│
├── src/sectra/
│   ├── ingestion/
│   │   ├── edgar_client.py      # rate-limited, cached SEC client
│   │   ├── company_resolver.py  # ticker -> CIK
│   │   ├── filing_downloader.py # filing index -> 10-K selection -> download
│   │   ├── download.py          # orchestration + manifests
│   │   ├── dataset_report.py    # docs/dataset.md
│   │   ├── load_manifests.py    # companies + filings -> MySQL
│   │   ├── xbrl_loader.py       # companyfacts -> financial_facts
│   │   ├── load_metric_map.py   # metric_map.csv -> MySQL
│   │   ├── chunker.py           # sections -> chunks.jsonl
│   │   ├── embed_chunks.py      # chunks -> cached vectors (checkpointed, resumable)
│   │   └── index_chunks.py      # vectors -> Qdrant
│   ├── parsing/
│   │   ├── html_text.py         # 10-K HTML -> clean text + anchors
│   │   ├── section_splitter.py  # text -> Items
│   │   └── build_sections.py    # all filings -> files + filing_sections + report
│   ├── storage/
│   │   ├── mysql.py             # SQLAlchemy engines from .env (owner and read-only)
│   │   ├── setup_reader.py      # creates the read-only MySQL user
│   │   └── vector_store.py      # Qdrant collection, upsert, filtered search
│   ├── retrieval/
│   │   ├── embedder.py          # embedding API client
│   │   ├── dense.py             # search_filings(): filtered vector search
│   │   ├── reranker.py          # rerank API client + reranked retriever
│   │   └── factory.py           # retriever by name: dense | rerank
│   ├── llm/
│   │   └── base.py              # provider-agnostic LLM client
│   ├── rag/
│   │   ├── answer.py            # retrieve -> prompt -> cite -> validate
│   │   └── ask.py               # CLI + run log
│   ├── agents/
│   │   ├── router.py            # route (sql | text | both | none) + deterministic corpus check
│   │   ├── nodes.py             # router, sql, text, writer, refuse as plain functions
│   │   └── graph.py             # LangGraph wiring, CLI, run log
│   ├── analyst/
│   │   ├── validator.py         # SELECT-only, allowlist, LIMIT; re-generates the query
│   │   ├── tools.py             # get_schema(), run_readonly_sql()
│   │   └── agent.py             # question -> SQL -> rows -> answer + number check; CLI
│   ├── api/
│   │   └── main.py              # FastAPI: /ask, /companies, /health; API key, rate limit, CORS
│   └── evaluation/
│       ├── qa_set.py            # generate, review, build and paraphrase the question sets
│       ├── retrieval_eval.py    # Recall@k, MRR, paired comparison
│       ├── threshold.py         # refusal-threshold sweep
│       ├── sql_eval.py          # execution accuracy of the SQL Analyst
│       └── routing_eval.py      # routing, routed retrieval, end-to-end refusal
│
├── tests/                       # 154 tests; fakes and SQLite instead of network calls
├── eval/
│   ├── datasets/                # retrieval question sets, sql_qa (46, with gold SQL), hybrid_qa (15)
│   └── results/                 # per-question results, experiments.md, section_parse_report.csv
├── docs/                        # see Section 4
└── data/                        # git-ignored; rebuilt by `make all`
```

---

## 9. Tech stack

| Layer | Choice | Status |
|---|---|---|
| Language | Python 3.12 | ✅ |
| Relational store | MySQL 8.4 (SQLAlchemy + PyMySQL) | ✅ |
| HTML parsing | lxml | ✅ |
| Token counting | Hugging Face `transformers` tokenizer (chunk sizing only) | ✅ |
| Embeddings | Hosted embedding API, 1,024-d (currently `nvidia/nemotron-3.5-embed-8b`) | ✅ |
| Vector store | Qdrant 1.18.2 (`qdrant-client` 1.18.0) | ✅ |
| Reranker | Hosted cross-encoder API (currently `nvidia/nemotron-3.5-rerank-8b`) | ✅ |
| LLM | Groq `openai/gpt-oss-120b` (default), Gemini, NVIDIA; `openai` SDK as OpenAI-compatible client | ✅ |
| Evaluation | Custom scripts: Recall@k, MRR, exact sign test, threshold sweep | ✅ |
| Tests | pytest | ✅ |
| Packaging | Docker, Docker Compose, `pyproject.toml`, Makefile | ✅ |
| Faithfulness judge | Claim-level LLM judge | Planned |
| SQL safety | `sqlglot` validator, read-only MySQL user, statement timeout | ✅ |
| Orchestration | LangGraph (state graph with conditional edges) | ✅ |
| API | FastAPI, uvicorn, Pydantic models | ✅ |
| Deployment | AWS EC2, Docker Compose | ✅ |
| CI/CD | GitHub Actions (pytest, deploy over SSH) | ✅ |
| Frontend | Web client over the API | Planned |

---

## 10. Limitations

- **Coverage:** 20 companies, 4 annual 10-Ks each. Numeric history reaches back to ~2009, but text covers only the downloaded filings.
- **Intel** (4 filings) has no extracted sections; its cross-reference format is not supported.
- **Metric normalization** is validated on a sample, not exhaustively; rare tags may be unmapped. Gaps are reported as NULL.
- **Per-share history** is not split-adjusted across filings.
- **No segment-level numbers** in SQL; they exist only in filing text.
- **The SQL Analyst is measured on 46 questions written alongside its prompt**, over one fact table and 15 metrics. The 100% second-run score is tuned on those questions; 93.5% is the first-run figure.
- **Fiscal years are each company's own.** "Fiscal 2025" ended in January 2025 for NVIDIA and December 2025 for AMD, so cross-company comparisons for one fiscal year cover different periods.
- **Routing is measured; hybrid answer quality is not.** The router sends some sector-level rankings to the hybrid path unnecessarily, and a subsidiary or brand name it does not know is refused.
- **Retrieval is measured on one kind of question:** 82 single-passage questions written and paraphrased by LLMs. Multi-passage, cross-company and cross-year questions are not measured.
- **Answer faithfulness is not measured yet.** Citation checks confirm that cited passages exist, not that they support each claim.
- **Out-of-corpus questions** (a company or year that is not indexed) are mostly caught by the model's refusal, not by retrieval scores.
- **The deployment is a single small instance over plain HTTP.** There is no HTTPS, load balancing or backup, the rate limiter is in memory, and the public IP changes if the instance is stopped. A browser frontend served over HTTPS will need TLS in front of the API.
- **Hosted APIs:** free endpoints are rate-limited, a content-safety filter refuses a few passages, models are not fully deterministic, and model names change as providers retire them.

---

*This project is for educational and portfolio purposes. It is not financial, investment, or legal advice. Filing data comes from the U.S. SEC's public EDGAR system; users are responsible for following the SEC's fair-access guidelines.*