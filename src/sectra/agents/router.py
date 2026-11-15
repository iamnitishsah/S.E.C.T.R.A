"""
Decide where a question goes, and whether the corpus can answer it at all.

    python -m sectra.agents.router "NVIDIA's revenue doubled in fiscal 2025. What did management say drove it?"

Two steps:
  1. route():        one LLM call -> route (sql | text | both | none), the companies and fiscal years
                     mentioned, and a sub-question for each side.
  2. check_corpus(): no LLM. Company names are matched to tickers in code, and each ticker and year
                     is checked against what is actually loaded. A question about a company or year
                     that is not indexed is refused here, before any retrieval or SQL.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ROUTES = ("sql", "text", "both", "none")
NAME_NOISE = {"inc", "corp", "corporation", "co", "company", "ltd", "limited", "nv", "de", "plc", "com", "the"}

ROUTER_SYSTEM = """You route questions for a research system over SEC 10-K annual reports. Two sources exist:

SQL: a database with one annual value per company and fiscal year for exactly these metrics:
{metrics}
It can also compute ratios, margins, growth rates, rankings and totals from them.

TEXT: the narrative sections of the 10-K filings (business description, risk factors, legal proceedings,
management's discussion and analysis). It explains reasons, risks, strategy, and holds details the
database lacks, such as segment or product revenue, employee counts and customer concentration.

Choose a route:
- "sql":  the question asks only for figures that the metrics above provide or that can be computed from them.
- "text": the question asks what a company said, described, expects or attributes something to, or asks for
          a figure that is NOT one of the metrics above.
- "both": the question needs a figure from the metrics AND explicitly asks for an explanation, a reason, a description, or what the company said. A ranking, comparison or total of figures alone is "sql", even when the question names a sector instead of a company.
- "none": investment advice, forecasts of the future, stock prices, personal information about people,
          or anything unrelated to these companies' annual reports.

Reply with one JSON object and nothing else:
{{"route": "sql" | "text" | "both" | "none",
  "companies": [company names or tickers exactly as the question writes them],
  "fiscal_years": [four-digit years the question names, as integers; empty if none],
  "sql_question": "the numeric part as a standalone question, or empty",
  "text_question": "the narrative part as a standalone question, or empty",
  "reason": "one short sentence"}}"""

JSON_RE = re.compile(r"\{.*\}", re.S)


@dataclass
class Catalog:
    """What is loaded: companies, the fiscal years with filing text, and the years with metrics."""
    companies: dict[str, dict]                      # ticker -> {"name", "sector"}
    text_years: dict[str, list[int]]                # ticker -> fiscal years with indexed filing text
    metric_years: dict[str, tuple[int, int]]        # ticker -> (first, last) fiscal year in financial_metrics
    metrics: list[str]
    aliases: dict[str, str] = field(default_factory=dict)


@dataclass
class Route:
    question: str
    route: str = "none"
    tickers: list[str] = field(default_factory=list)
    unknown_companies: list[str] = field(default_factory=list)
    fiscal_years: list[int] = field(default_factory=list)
    text_years: dict[str, int] = field(default_factory=dict)    # ticker -> fiscal year to search (default: latest)
    sql_question: str = ""
    text_question: str = ""
    reason: str = ""                                # the router's own explanation
    refused: bool = False
    refusal: str = ""                               # why the corpus cannot answer
    notes: list[str] = field(default_factory=list)  # e.g. a "both" question reduced to one side
    fallback: bool = False                          # the router's reply could not be parsed
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0


def normalize_name(name: str) -> str:
    words = re.sub(r"[^a-z0-9& ]", " ", name.lower().replace("/", " ")).replace("&", " ").split()
    return " ".join(w for w in words if w not in NAME_NOISE)


def resolve_company(mention: str, catalog: Catalog) -> str | None:
    """A company name or ticker as written -> ticker, or None if it is not one of the indexed companies."""
    raw = mention.strip()
    if raw.upper() in catalog.companies:
        return raw.upper()
    alias = catalog.aliases.get(raw.lower()) or catalog.aliases.get(normalize_name(raw))
    if alias:
        return alias
    m = normalize_name(raw)
    if not m:
        return None
    hits = [t for t, c in catalog.companies.items()
            if (n := normalize_name(c["name"])) == m or n.startswith(m + " ") or m.startswith(n + " ")]
    return hits[0] if len(hits) == 1 else None


def parse_reply(reply: str) -> dict | None:
    m = JSON_RE.search(reply)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("route") not in ROUTES:
        return None
    return data


def _years(values) -> list[int]:
    out = []
    for v in values if isinstance(values, list) else []:
        if str(v).strip().isdigit() and 1990 <= int(v) <= 2100 and int(v) not in out:
            out.append(int(v))
    return sorted(out)


def route(question: str, llm, catalog: Catalog, temperature: float = 0.0, max_tokens: int = 2000) -> Route:
    """LLM step: classify the question and extract what it mentions. One retry if the reply is not valid JSON."""
    r = Route(question)
    system = ROUTER_SYSTEM.format(metrics=", ".join(catalog.metrics))
    data = None
    for attempt in range(2):
        user = f"Question: {question}" + ("\n\nReply with the JSON object only." if attempt else "")
        resp = llm.complete(system, user, temperature, max_tokens)
        r.input_tokens += resp.input_tokens
        r.output_tokens += resp.output_tokens
        r.latency_s += resp.latency_s
        data = parse_reply(resp.text)
        if data:
            break
    if not data:                                    # cannot classify: search the filings, the safer default
        r.route, r.text_question, r.fallback, r.reason = "text", question, True, "router reply could not be parsed"
        return r

    r.route, r.reason = data["route"], str(data.get("reason", ""))[:300]
    r.fiscal_years = _years(data.get("fiscal_years"))
    r.sql_question = str(data.get("sql_question") or "").strip()
    r.text_question = str(data.get("text_question") or "").strip()
    for mention in data.get("companies") if isinstance(data.get("companies"), list) else []:
        ticker = resolve_company(str(mention), catalog)
        if ticker and ticker not in r.tickers:
            r.tickers.append(ticker)
        elif not ticker and str(mention) not in r.unknown_companies:
            r.unknown_companies.append(str(mention))
    if r.route in ("sql", "both") and not r.sql_question:
        r.sql_question = question
    if r.route in ("text", "both") and not r.text_question:
        r.text_question = question
    return r


def check_corpus(r: Route, catalog: Catalog) -> Route:
    """Deterministic step: refuse, or reduce a 'both' question, when the corpus lacks the company or year."""
    if r.route == "none":
        r.refused, r.refusal = True, r.reason or "the question is outside what the filings and the database cover"
        return r
    if r.unknown_companies:
        r.refused = True
        r.refusal = (f"not among the indexed companies: {', '.join(r.unknown_companies)} "
                     f"(indexed: {', '.join(sorted(catalog.companies))})")
        return r

    sql_problem = text_problem = ""
    for t in r.tickers:
        lo, hi = catalog.metric_years.get(t, (0, 0))
        bad = [y for y in r.fiscal_years if not lo <= y <= hi]
        if bad and not sql_problem:
            sql_problem = f"the database has {t} for fiscal {lo}-{hi}, not {', '.join(map(str, bad))}"
        years = catalog.text_years.get(t, [])
        if not years:
            text_problem = text_problem or f"no filing text is indexed for {t}"
            continue
        missing = [y for y in r.fiscal_years if y not in years]
        if missing:
            text_problem = text_problem or (f"no {t} 10-K is indexed for fiscal {', '.join(map(str, missing))} "
                                            f"(indexed: {', '.join(map(str, years))})")
        else:                                       # no year named: search the latest filing, not every year
            r.text_years[t] = max(r.fiscal_years) if r.fiscal_years else max(years)

    if r.route == "sql" and sql_problem:
        r.refused, r.refusal = True, sql_problem
    elif r.route == "text" and text_problem:
        r.refused, r.refusal = True, text_problem
    elif r.route == "both":
        if sql_problem and text_problem:
            r.refused, r.refusal = True, f"{sql_problem}; {text_problem}"
        elif text_problem:
            r.route = "sql"
            r.notes.append(f"answering the numeric part only: {text_problem}")
        elif sql_problem:
            r.route = "text"
            r.notes.append(f"answering the narrative part only: {sql_problem}")
    return r


def load_catalog(engine, root: Path = ROOT) -> Catalog:  # pragma: no cover - needs MySQL
    from sqlalchemy import text
    with engine.connect() as conn:
        companies = {t: {"name": n, "sector": s} for t, n, s in
                     conn.execute(text("SELECT ticker, name, sector FROM companies"))}
        text_years: dict[str, list[int]] = {}
        for t, fy in conn.execute(text(
                "SELECT DISTINCT c.ticker, f.fiscal_year FROM filing_sections s "
                "JOIN filings f ON f.accession_no = s.accession_no JOIN companies c ON c.cik = f.cik "
                "WHERE f.fiscal_year IS NOT NULL ORDER BY c.ticker, f.fiscal_year")):
            text_years.setdefault(t, []).append(int(fy))
        metric_years = {t: (int(lo), int(hi)) for t, lo, hi in conn.execute(text(
            "SELECT ticker, MIN(fiscal_year), MAX(fiscal_year) FROM financial_metrics GROUP BY ticker"))}
        metrics = [m for (m,) in conn.execute(text(
            "SELECT DISTINCT canonical_metric FROM financial_metrics ORDER BY canonical_metric"))]
    cfg = yaml.safe_load(open(root / "configs" / "agents.yaml")) or {}
    aliases = {str(k).lower(): str(v).upper() for k, v in (cfg.get("aliases") or {}).items()}
    return Catalog(companies, text_years, metric_years, metrics, aliases)


def main() -> None:  # pragma: no cover - needs MySQL + an API key
    import sys

    from dotenv import load_dotenv

    from sectra.llm.base import get_llm
    from sectra.storage.mysql import get_engine
    load_dotenv(ROOT / ".env")
    catalog = load_catalog(get_engine())
    r = check_corpus(route(sys.argv[1], get_llm(), catalog), catalog)
    print(f"route:    {r.route}{'  (REFUSED)' if r.refused else ''}{'  (fallback)' if r.fallback else ''}")
    print(f"tickers:  {r.tickers}   years: {r.fiscal_years}   text years: {r.text_years}")
    if r.unknown_companies:
        print(f"unknown:  {r.unknown_companies}")
    print(f"sql:      {r.sql_question}\ntext:     {r.text_question}\nreason:   {r.reason}")
    if r.refusal:
        print(f"refusal:  {r.refusal}")
    for note in r.notes:
        print(f"note:     {note}")
    print(f"[{r.input_tokens} in / {r.output_tokens} out tokens | {r.latency_s:.1f}s]")


if __name__ == "__main__":
    main()