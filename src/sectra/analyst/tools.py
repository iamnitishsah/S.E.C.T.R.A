"""
The two tools the SQL Analyst uses: describe the data, and run a validated read-only query.

    python -m sectra.analyst.tools                       # print the schema text the model will see
    python -m sectra.analyst.tools "SELECT ticker, value FROM financial_metrics WHERE ..."
"""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from sectra.analyst.validator import UnsafeSQL, validate

ROOT = Path(__file__).resolve().parents[3]

SCHEMA_TEXT = """Tables (MySQL 8). Use only these.

financial_metrics: one row per company, fiscal year and metric. Annual values only.
  cik CHAR(10)              company id (join key to companies and filings)
  ticker VARCHAR            e.g. 'NVDA'
  sector VARCHAR            one of the sectors listed below
  fiscal_year SMALLINT      the company's own fiscal year, e.g. 2025
  canonical_metric VARCHAR  one of the metric names listed below
  value DECIMAL             full units, not thousands or millions (USD, shares, or USD per share)
  unit VARCHAR              'USD', 'shares' or 'USD/shares'
  period_end DATE           last day of that fiscal year
  source_tag VARCHAR        the XBRL tag the value came from
  source_accession CHAR(20) the filing that reported the value (the citation for the number)

companies: one row per company.
  cik, ticker, name, sector, sic, sic_description, exchange
  fiscal_year_end CHAR(4)   MMDD, e.g. '0927'

filings: the downloaded 10-K reports (four per company).
  accession_no CHAR(20), cik, form_type, filing_date DATE, period_of_report DATE,
  fiscal_year SMALLINT, primary_doc_url VARCHAR (link to the document on sec.gov)

Notes:
  - Each metric is a separate ROW, not a column. Filter with canonical_metric = '...'.
  - To combine two metrics, join financial_metrics to itself on cik and fiscal_year.
  - A metric a company does not report has NO row (it is not zero).
  - Fiscal years differ between companies: NVIDIA's fiscal 2026 ends in January 2026.
  - Always select ticker, fiscal_year and source_accession with the values."""


@dataclass
class QueryResult:
    ok: bool
    sql: str = ""                                   # the query that was executed (validated, LIMIT enforced)
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    truncated: bool = False                         # the LIMIT was reached, so more rows may exist
    error: str = ""                                 # why it failed; shown to the model so it can fix the query
    elapsed_ms: int = 0


def load_config(root: Path = ROOT) -> dict:
    return yaml.safe_load(open(root / "configs" / "sql.yaml"))


def _plain(value):
    """Database values -> JSON-friendly values (Decimal keeps whole numbers exact)."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


def run_readonly_sql(sql: str, engine, cfg: dict) -> QueryResult:
    """Validate, then execute. Never raises for a bad query: the reason comes back in `error`."""
    try:
        q = validate(sql, cfg["allowed_tables"], cfg["max_rows"])
    except UnsafeSQL as exc:
        return QueryResult(False, error=f"rejected: {exc}")
    t0 = time.monotonic()
    try:
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text(f"SET SESSION MAX_EXECUTION_TIME = {int(cfg['timeout_ms'])}"))
            result = conn.execute(text(q.sql.replace(":", r"\:")))
            columns = list(result.keys())
            rows = [[_plain(v) for v in row] for row in result]
    except SQLAlchemyError as exc:
        reason = str(getattr(exc, "orig", exc)).splitlines()[0][:300]
        return QueryResult(False, sql=q.sql, error=f"database error: {reason}",
                           elapsed_ms=int((time.monotonic() - t0) * 1000))
    truncated = q.limit == cfg["max_rows"] and len(rows) >= q.limit
    return QueryResult(True, q.sql, columns, rows, truncated=truncated,
                       elapsed_ms=int((time.monotonic() - t0) * 1000))


def get_schema(engine) -> str:
    """Schema text plus what the data actually contains: sectors, tickers, years, metric coverage."""
    with engine.connect() as conn:
        companies = conn.execute(text("SELECT sector, ticker, name FROM companies ORDER BY sector, ticker")).all()
        lo, hi = conn.execute(text("SELECT MIN(fiscal_year), MAX(fiscal_year) FROM financial_metrics")).one()
        latest = conn.execute(text(
            "SELECT fiscal_year FROM financial_metrics GROUP BY fiscal_year "
            "ORDER BY COUNT(DISTINCT cik) DESC, fiscal_year DESC LIMIT 1")).scalar()
        metrics = conn.execute(text(
            "SELECT canonical_metric, MIN(unit), COUNT(DISTINCT cik) FROM financial_metrics "
            "WHERE fiscal_year = :fy GROUP BY canonical_metric ORDER BY canonical_metric"), {"fy": latest}).all()
    by_sector: dict[str, list[str]] = {}
    for sector, ticker, name in companies:
        by_sector.setdefault(sector, []).append(f"{ticker} ({name})")
    lines = [SCHEMA_TEXT, "", "Sectors and tickers:"]
    lines += [f"  {sector}: {', '.join(tickers)}" for sector, tickers in by_sector.items()]
    lines += ["", f"Fiscal years in financial_metrics: {lo} to {hi}.",
              f"Default fiscal year when the question names none: {latest} (the latest year every company has).",
              "", f"Metric names (unit; companies reporting it in fiscal {latest}, of {len(companies)}):"]
    lines += [f"  {name} ({unit}; {n})" for name, unit, n in metrics]
    return "\n".join(lines)


def format_rows(result: QueryResult, max_rows: int = 30) -> str:
    """Compact text table of a result, for the terminal and for the model."""
    if not result.ok:
        return result.error
    if not result.rows:
        return "(no rows)"
    shown = [[("" if v is None else str(v)) for v in row] for row in result.rows[:max_rows]]
    widths = [max(len(c), *(len(r[i]) for r in shown)) for i, c in enumerate(result.columns)]
    out = ["  ".join(c.ljust(w) for c, w in zip(result.columns, widths))]
    out += ["  ".join(v.ljust(w) for v, w in zip(row, widths)) for row in shown]
    if len(result.rows) > max_rows:
        out.append(f"... {len(result.rows) - max_rows} more rows")
    return "\n".join(out)


def main() -> None:  # pragma: no cover - needs MySQL
    import sys

    from sectra.storage.mysql import get_reader_engine
    engine = get_reader_engine()
    if len(sys.argv) < 2:
        print(get_schema(engine))
        return
    result = run_readonly_sql(sys.argv[1], engine, load_config())
    print(result.sql or sys.argv[1])
    print(format_rows(result))
    if result.ok:
        print(f"[{len(result.rows)} rows, {result.elapsed_ms} ms{', LIMIT reached' if result.truncated else ''}]")


if __name__ == "__main__":
    main()