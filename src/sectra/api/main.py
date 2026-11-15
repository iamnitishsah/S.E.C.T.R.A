"""HTTP API over the research graph.

    uvicorn sectra.api.main:app --reload                 # local: http://localhost:8000/docs
    uvicorn sectra.api.main:app --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health      is the process up, and what is loaded
    GET  /companies   the indexed companies and the fiscal years available for each
    POST /ask         {"question": "..."} -> answer, evidence (table and passages), checks, step trace

The graph, the retriever and the database connections are built once at startup and reused, so a
request pays only for its own LLM, embedding and rerank calls.

Settings come from the environment (.env):
    SECTRA_API_KEY       if set, /ask requires the header  X-API-Key: <value>
    CORS_ORIGINS         comma-separated origins allowed to call the API from a browser
    RATE_LIMIT_PER_MIN   requests per minute per client IP on /ask (default 20; 0 disables)
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

log = logging.getLogger("sectra.api")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500,
                          examples=["How fast did Nvidia's revenue grow in fiscal 2025, and what drove it?"])


class Table(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list]
    source_filings: list[str]


class Passage(BaseModel):
    n: int                      # the number used in [n] citations
    cited: bool
    header: str
    text: str
    score: float
    chunk_id: str
    ticker: str | None = None
    fiscal_year: int | None = None
    item_code: str | None = None
    url: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    route: str                  # sql | text | both | none
    answered: bool              # False when the system declined
    reason: str = ""            # why it declined
    tickers: list[str] = []
    fiscal_years: list[int] = []
    table: Table | None = None  # cited as [T]
    passages: list[Passage] = []
    warnings: dict = {}         # uncited sentences, numbers not in the evidence, invalid citations, truncation
    steps: list[str] = []
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class Company(BaseModel):
    ticker: str
    name: str
    sector: str
    text_years: list[int]       # fiscal years with indexed filing text
    metric_years: list[int]     # [first, last] fiscal year with financial metrics


class RateLimiter:
    """At most `per_minute` calls per key in any 60-second window (in memory, one process)."""

    def __init__(self, per_minute: int):
        self.per_minute, self.calls = per_minute, defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.per_minute <= 0:
            return True
        now = time.monotonic() if now is None else now
        q = self.calls[key]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


def to_response(state: dict, latency_ms: int) -> AskResponse:
    """Graph state -> the JSON the client gets."""
    r, sql, checks = state["route"], state.get("sql"), state.get("checks") or {}
    cited = set(checks.get("cited_passages", []))
    table = None
    if sql is not None and not sql.cannot_answer:
        table = Table(sql=sql.sql, columns=sql.columns, rows=sql.rows, source_filings=sql.sources)
    passages = [Passage(n=n, cited=n in cited, header=p["header"], text=p["text"], score=round(float(p["score"]), 4),
                        chunk_id=p["chunk_id"], ticker=p.get("ticker"), fiscal_year=p.get("fiscal_year"),
                        item_code=p.get("item_code"), url=p.get("source_url"))
                for n, p in enumerate(state.get("passages") or [], start=1)]
    warnings = {k: v for k, v in checks.items()
                if k in ("uncited_sentences", "unsupported_numbers", "invalid_citations", "truncated") and v}
    usage = state.get("usage") or {}
    return AskResponse(question=state["question"], answer=state.get("answer", ""), route=r.route,
                       answered=not state.get("not_found", False), reason=state.get("reason", ""), tickers=r.tickers,
                       fiscal_years=r.fiscal_years, table=table, passages=passages, warnings=warnings,
                       steps=state.get("trace", []), model=state.get("model", ""),
                       input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
                       latency_ms=latency_ms)


def create_app(deps=None) -> FastAPI:
    """`deps` is passed by tests; in production it is built at startup from .env and configs/."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from sectra.agents.graph import build_graph, make_deps
        app.state.deps = deps or make_deps()
        app.state.graph = build_graph(app.state.deps)
        log.info("ready: %d companies", len(app.state.deps.catalog.companies))
        yield

    app = FastAPI(title="S.E.C.T.R.A", version="0.1.0", lifespan=lifespan,
                  description="Research over SEC 10-K filings: figures from a validated database, "
                              "explanations from cited filing text.")
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
               if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])
    limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MIN", "20")))

    def guard(request: Request, x_api_key: str | None = Header(default=None)) -> None:
        expected = os.getenv("SECTRA_API_KEY")
        if expected and x_api_key != expected:
            raise HTTPException(status_code=401, detail="missing or wrong X-API-Key header")
        client = request.client.host if request.client else "unknown"
        if not limiter.allow(client):
            raise HTTPException(status_code=429, detail="too many requests; try again in a minute")

    @app.get("/health")
    def health(request: Request) -> dict:
        d = request.app.state.deps
        return {"status": "ok", "companies": len(d.catalog.companies), "metrics": len(d.catalog.metrics),
                "llm": getattr(d.llm, "model", None)}

    @app.get("/companies", response_model=list[Company])
    def companies(request: Request) -> list[Company]:
        c = request.app.state.deps.catalog
        return [Company(ticker=t, name=v["name"], sector=v["sector"], text_years=c.text_years.get(t, []),
                        metric_years=list(c.metric_years.get(t, ())))
                for t, v in sorted(c.companies.items())]

    @app.post("/ask", response_model=AskResponse, dependencies=[Depends(guard)])
    def ask(body: AskRequest, request: Request) -> AskResponse:
        t0 = time.monotonic()
        try:
            state = request.app.state.graph.invoke({"question": body.question.strip()})
        except Exception:                                   # an upstream API or database failure
            log.exception("ask failed: %s", body.question)
            raise HTTPException(status_code=502, detail="the question could not be processed; try again") from None
        resp = to_response(state, int((time.monotonic() - t0) * 1000))
        try:
            from sectra.agents.graph import log_run
            log_run(state, getattr(request.app.state.deps.llm, "name", ""))
        except OSError:
            log.warning("could not write the run log")
        return resp

    return app


app = create_app()