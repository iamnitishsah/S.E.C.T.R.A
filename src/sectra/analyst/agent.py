"""SQL Analyst: question -> SQL -> validated read-only query -> answer written from the rows.

    python -m sectra.analyst.agent "Which semiconductor company had the highest net income in fiscal 2025?"
    python -m sectra.analyst.agent "..." --backend gemini --show-sql

Flow:
  1. The model sees the schema and the question and returns one SELECT, or CANNOT_ANSWER: <reason>.
  2. The query is validated and run by run_readonly_sql. If it is rejected or fails, the error
     goes back to the model, up to `max_attempts` queries in total.
  3. A second call writes a short answer from the result table only.
  4. Every number in the answer is checked against the rows (and the question); the rest are flagged.

All arithmetic happens in SQL, never in the model. Every run is appended to data/logs/sql.jsonl.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sectra.analyst.tools import QueryResult, format_rows, get_schema, load_config, run_readonly_sql

ROOT = Path(__file__).resolve().parents[3]

SQL_SYSTEM = """You write MySQL 8 queries over a database of annual financial metrics from SEC 10-K filings.

{schema}

Rules:
1. Reply with exactly one SELECT statement inside a ```sql code block, and nothing else.
2. If the question cannot be answered from these tables (a metric that is not in the list, quarterly data,
   stock prices, forecasts, opinions, a company that is not listed), reply instead with exactly:
   CANNOT_ANSWER: <one sentence saying what is missing>
3. Do every calculation in SQL: ratios, margins, growth rates, differences, rankings.
   - Margin or ratio: join financial_metrics to itself on cik and fiscal_year.
   - Year-over-year growth: join the same metric on cik with fiscal_year = prior.fiscal_year + 1.
   - Percentages: ROUND(100 * a / b, 2) with a column name ending in _pct.
   - USD amounts: ROUND(value / 1e9, 2) with a column name ending in _bn. Keep per-share values as they are.
4. Always select ticker and fiscal_year, and source_accession for every value used.
5. A metric a company does not report has no row. Never replace a missing value with 0.
6. Use only the column names, metric names, sectors and tickers shown above.
7. If the question names no fiscal year, use the default fiscal year given above, and only that year.
8. Return only the fiscal years the question asks about. A comparison of two years is one row, for the later year."""

ANSWER_SYSTEM = """You answer a question about company financials using ONLY the result table of a SQL query.

Rules:
1. Copy numbers exactly as they appear in the table. Do not calculate, round, convert or estimate anything.
2. Say which company and fiscal year each number belongs to. Column names ending in _bn are billions of
   US dollars; names ending in _pct are percentages.
3. If the table is empty, say the database has no such data and that the metric may not be reported by
   that company or for that year. Do not guess a value.
4. If the table does not answer the whole question, say which part is missing.
5. Write for a reader, not a database: use company names, never column names or accession numbers
   (the source filings are listed separately)."""

SQL_BLOCK_RE = re.compile(r"```(?:sql|mysql)?\s*(.*?)```", re.S | re.I)
NUMBER_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?!\d*-[KQ]\b)")   # skips the 10 in "10-K"


@dataclass
class SQLAnswer:
    question: str
    text: str
    sql: str = ""                                   # the query whose rows the answer is based on
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    attempts: list[dict] = field(default_factory=list)     # every query tried: {"sql", "error"}
    cannot_answer: bool = False
    reason: str = ""
    sources: list[str] = field(default_factory=list)       # accession numbers found in the rows
    unsupported_numbers: list[str] = field(default_factory=list)
    truncated: bool = False
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0


def extract_sql(reply: str) -> str:
    """The query inside a ```sql block, or the whole reply if it already is a bare query."""
    m = SQL_BLOCK_RE.search(reply)
    return (m.group(1) if m else reply).strip().rstrip(";").strip()


def build_sql_prompt(question: str, attempts: list[dict]) -> str:
    parts = [f"Question: {question}"]
    for n, a in enumerate(attempts, start=1):
        parts.append(f"\nYour query {n}:\n```sql\n{a['sql']}\n```\nIt failed: {a['error']}")
    if attempts:
        parts.append("\nWrite a corrected query.")
    return "\n".join(parts)


def _numbers(text: str) -> list[tuple[str, float, int]]:
    """(as written, value, decimals written) for each number in a text."""
    out = []
    for raw in NUMBER_RE.findall(text):
        raw = raw.rstrip(",")
        clean = raw.replace(",", "")
        try:
            out.append((raw, float(clean), len(clean.split(".")[1]) if "." in clean else 0))
        except ValueError:
            continue
    return out


def unsupported_numbers(answer: str, result: QueryResult, question: str) -> list[str]:
    """Numbers in the answer that are neither in the result rows nor in the question.

    A number matches a row value if the row value, rounded to the decimals the answer wrote,
    is equal to it (so 63.9 matches 63.89, but 64 does not match 63.49).
    """
    known = [float(v) for row in result.rows for v in row if isinstance(v, (int, float)) and not isinstance(v, bool)]
    known += [v for row in result.rows for cell in row if isinstance(cell, str) for _, v, _ in _numbers(cell)]
    known += [v for _, v, _ in _numbers(question)]
    known.append(float(len(result.rows)))                        # "three companies ..." written as a digit
    bad = []
    for raw, value, decimals in _numbers(answer):
        if not any(abs(abs(round(k, decimals)) - abs(value)) < 1e-9 for k in known) and raw not in bad:
            bad.append(raw)
    return bad


def ask_sql(question: str, llm, engine, cfg: dict, schema: str | None = None, max_attempts: int = 3,
            temperature: float = 0.0, max_tokens: int = 2000) -> SQLAnswer:
    schema = schema or get_schema(engine)
    ans = SQLAnswer(question, "")
    result = None

    def call(system: str, user: str):
        resp = llm.complete(system, user, temperature, max_tokens)
        ans.model, ans.latency_s = resp.model, ans.latency_s + resp.latency_s
        ans.input_tokens += resp.input_tokens
        ans.output_tokens += resp.output_tokens
        return resp.text.strip()

    for _ in range(max_attempts):
        reply = call(SQL_SYSTEM.format(schema=schema), build_sql_prompt(question, ans.attempts))
        if reply.upper().startswith("CANNOT_ANSWER"):
            ans.cannot_answer, ans.reason = True, reply.split(":", 1)[-1].strip()
            ans.text = "This cannot be answered from the financial database."
            return ans
        result = run_readonly_sql(extract_sql(reply), engine, cfg)
        ans.attempts.append({"sql": result.sql or extract_sql(reply), "error": result.error})
        if result.ok:
            break
    if result is None or not result.ok:
        ans.cannot_answer, ans.reason = True, f"no working query after {max_attempts} attempts"
        ans.text = "This could not be answered: the generated queries failed."
        return ans

    ans.sql, ans.columns, ans.rows, ans.truncated = result.sql, result.columns, result.rows, result.truncated
    acc_cols = [i for i, c in enumerate(result.columns) if "accession" in c.lower()]
    ans.sources = sorted({row[i] for row in result.rows for i in acc_cols if row[i]})
    ans.text = call(ANSWER_SYSTEM, f"Question: {question}\n\nSQL:\n{result.sql}\n\nResult table "
                                   f"({len(result.rows)} rows):\n{format_rows(result, max_rows=50)}")
    ans.unsupported_numbers = unsupported_numbers(ans.text, result, question)
    return ans


def log_run(ans: SQLAnswer, backend: str) -> None:
    path = ROOT / "data" / "logs" / "sql.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "question": ans.question,
              "backend": backend, "model": ans.model, "sql": ans.sql, "attempts": ans.attempts,
              "n_rows": len(ans.rows), "answer": ans.text, "cannot_answer": ans.cannot_answer,
              "reason": ans.reason, "sources": ans.sources, "unsupported_numbers": ans.unsupported_numbers,
              "input_tokens": ans.input_tokens, "output_tokens": ans.output_tokens,
              "latency_s": round(ans.latency_s, 2)}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_answer(ans: SQLAnswer, show_sql: bool) -> None:
    print("\n" + "=" * 80)
    print(ans.text)
    if ans.cannot_answer:
        print(f"\n(reason: {ans.reason})")
    if ans.rows:
        print("\n" + format_rows(QueryResult(True, ans.sql, ans.columns, ans.rows), max_rows=15))
    if ans.truncated:
        print("\n!! the row limit was reached; the result may be incomplete")
    if ans.unsupported_numbers:
        print(f"\n!! numbers in the answer that are not in the result: {', '.join(ans.unsupported_numbers)}")
    failed = [a for a in ans.attempts if a["error"]]
    if failed:
        print(f"\n({len(failed)} failed attempt(s) before this: {failed[-1]['error'][:120]})")
    if show_sql or failed:
        for n, a in enumerate(ans.attempts, start=1):
            print(f"\n--- query {n}{' (failed)' if a['error'] else ''}\n{a['sql']}")
    if ans.sources:
        print(f"\nSource filings: {', '.join(ans.sources)}")
    if ans.model:
        print(f"\n[{ans.model} | {ans.input_tokens} in / {ans.output_tokens} out tokens | {ans.latency_s:.1f}s]")


def main() -> None:  # pragma: no cover - needs MySQL + an API key
    from dotenv import load_dotenv

    from sectra.llm.base import get_llm
    from sectra.llm.base import load_config as load_llm_config
    from sectra.storage.mysql import get_reader_engine

    p = argparse.ArgumentParser(description="Ask the financial database a question.")
    p.add_argument("question")
    p.add_argument("--backend", help="LLM backend from configs/llm.yaml")
    p.add_argument("--show-sql", action="store_true")
    args = p.parse_args()

    load_dotenv(ROOT / ".env")
    gen = load_llm_config().get("generation", {})
    llm = get_llm(args.backend)
    print(f"[backend: {llm.name} / {llm.model}  (chosen by {llm.source})]")
    ans = ask_sql(args.question, llm, get_reader_engine(), load_config(),
                  temperature=gen.get("temperature", 0.0), max_tokens=gen.get("max_tokens", 2000))
    print_answer(ans, args.show_sql)
    log_run(ans, llm.name)


if __name__ == "__main__":
    main()