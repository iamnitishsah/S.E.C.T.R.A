"""
Measure the SQL Analyst on eval/datasets/sql_qa.jsonl.

    python -m sectra.evaluation.sql_eval --check-gold        # run only the gold queries and show their results
    python -m sectra.evaluation.sql_eval                     # run the agent on every question and score it
    python -m sectra.evaluation.sql_eval --backend gemini --limit 10

Scoring is by RESULT, not by SQL text (execution accuracy):
  expect "rows"     pass if the agent's rows hold the same companies / sectors / years as the gold rows,
                    with the same values (within rounding, in any unit scale), and no extra rows
  expect "no_data"  pass if the agent declines or returns no rows; fail if it returns any value
Results are saved per question to eval/results/sql_eval_<backend>.json.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from sectra.analyst.tools import QueryResult, format_rows, get_schema, load_config, run_readonly_sql
from sectra.evaluation.qa_set import load_jsonl

ROOT = Path(__file__).resolve().parents[3]
KEY_COLUMNS = ("ticker", "sector", "fiscal_year")
SCALES = (1, 1e-9, 1e-6, 1e-3, 1e2, 1e3, 1e6, 1e9)         # billions vs raw dollars, percent vs fraction, ...


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def values_match(gold: float, pred: float) -> bool:
    tol = max(0.006, 0.002 * abs(gold))
    return any(abs(pred * s - gold) <= tol for s in SCALES)


def _group(columns: list[str], rows: list[list], keys: list[str]) -> dict[tuple, list[float]]:
    """key (e.g. ticker, fiscal_year) -> every other numeric value in the rows with that key."""
    names = [c.lower() for c in columns]
    key_idx = [names.index(k) for k in keys]
    out: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row[i]).upper() for i in key_idx)
        out[key] += [float(v) for i, v in enumerate(row) if i not in key_idx and names[i] not in KEY_COLUMNS
                     and _is_number(v)]
    return out


def compare(gold: QueryResult, pred: QueryResult) -> tuple[bool, str]:
    """Does the predicted result contain the gold result and nothing more? -> (passed, reason)."""
    gold_names, pred_names = [c.lower() for c in gold.columns], [c.lower() for c in pred.columns]
    if "ticker" in gold_names and "ticker" not in pred_names:
        return False, "the result has no ticker column"
    keys = [k for k in KEY_COLUMNS if k in gold_names and k in pred_names]
    g, p = _group(gold.columns, gold.rows, keys), _group(pred.columns, pred.rows, keys)
    if not keys and len(gold.rows) != len(pred.rows):
        return False, f"expected {len(gold.rows)} rows, got {len(pred.rows)}"
    missing, extra = sorted(set(g) - set(p)), sorted(set(p) - set(g))
    if missing or extra:
        return False, f"rows differ: missing {missing[:5]}, extra {extra[:5]}"
    for key, gold_values in g.items():
        for value in gold_values:
            if not any(values_match(value, v) for v in p[key]):
                return False, f"{key}: expected {value}, got {p[key]}"
    return True, ""


def score(q: dict, ans, gold: QueryResult | None) -> tuple[bool, str]:
    returned_data = bool(ans.rows)
    if q["expect"] == "no_data":
        return (not returned_data), ("returned rows where no data exists" if returned_data else "")
    if ans.cannot_answer:
        return False, f"declined: {ans.reason}"
    return compare(gold, QueryResult(True, ans.sql, ans.columns, ans.rows))


def check_gold(questions: list[dict], engine, cfg: dict) -> None:
    problems = 0
    for q in questions:
        if not q["gold_sql"]:
            continue
        r = run_readonly_sql(q["gold_sql"], engine, cfg)
        flag = ""
        if not r.ok:
            flag = "   <-- GOLD QUERY FAILED"
        elif q["expect"] == "rows" and not r.rows:
            flag = "   <-- expected rows, gold returned none"
        elif q["expect"] == "no_data" and r.rows:
            flag = "   <-- expected no data, gold returned rows"
        problems += bool(flag)
        print(f"\n{q['id']} [{q['type']}] {q['question']}{flag}")
        print("  " + format_rows(r, max_rows=8).replace("\n", "\n  "))
    print(f"\n{problems} gold queries need attention" if problems else "\nall gold queries behave as expected")


def report(records: list[dict]) -> dict:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_type[r["type"]].append(r)
    print(f"\n{'type':15} {'n':>3} {'passed':>7} {'accuracy':>9}")
    for name in sorted(by_type):
        rows = by_type[name]
        print(f"{name:15} {len(rows):>3} {sum(r['passed'] for r in rows):>7} {sum(r['passed'] for r in rows) / len(rows):>9.1%}")
    n, passed = len(records), sum(r["passed"] for r in records)
    print(f"{'ALL':15} {n:>3} {passed:>7} {passed / n:>9.1%}")

    ran = [r for r in records if r["attempts"]]
    retried = [r for r in ran if len(r["attempts"]) > 1]
    answered = [r for r in records if r["n_rows"]]
    flagged = [r for r in answered if r["unsupported_numbers"]]
    no_data = Counter("declined" if r["cannot_answer"] else "empty result" if not r["n_rows"] else "returned rows"
                      for r in records if r["expect"] == "no_data")
    print(f"\nqueries that needed a retry: {len(retried)} of {len(ran)}")
    print(f"answers containing a number that is not in the rows: {len(flagged)} of {len(answered)}")
    print(f"questions with no data in the database: {dict(no_data)}")
    print(f"mean latency {sum(r['latency_s'] for r in records) / n:.1f}s, "
          f"mean tokens {sum(r['input_tokens'] + r['output_tokens'] for r in records) / n:.0f}")

    failures = [r for r in records if not r["passed"]]
    if failures:
        print(f"\nfailures ({len(failures)}):")
        for r in failures:
            print(f"\n  {r['id']} [{r['type']}] {r['question']}\n    why:  {r['why']}")
            print(f"    gold: {r['gold_sql']}\n    got:  {r['sql'] or '(no query)'}")
    return {"n": n, "passed": passed, "accuracy": round(passed / n, 3),
            "by_type": {k: round(sum(r["passed"] for r in v) / len(v), 3) for k, v in by_type.items()},
            "retried": len(retried), "unsupported_number_answers": len(flagged)}


def main() -> None:  # pragma: no cover - needs MySQL + an API key
    from dotenv import load_dotenv

    from sectra.analyst.agent import ask_sql
    from sectra.llm.base import get_llm
    from sectra.llm.base import load_config as load_llm_config
    from sectra.storage.mysql import get_reader_engine

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-gold", action="store_true")
    p.add_argument("--backend")
    p.add_argument("--limit", type=int)
    p.add_argument("--sleep", type=float, default=2.0, help="seconds between questions (free-tier rate limits)")
    args = p.parse_args()

    load_dotenv(ROOT / ".env")
    questions = load_jsonl(ROOT / "eval/datasets/sql_qa.jsonl")[: args.limit]
    engine, cfg = get_reader_engine(), load_config()
    if args.check_gold:
        check_gold(questions, engine, cfg)
        return

    llm, gen, schema = get_llm(args.backend), load_llm_config().get("generation", {}), get_schema(engine)
    print(f"[backend: {llm.name} / {llm.model}]")
    records = []
    for n, q in enumerate(questions, start=1):
        ans = ask_sql(q["question"], llm, engine, cfg, schema=schema,
                      temperature=gen.get("temperature", 0.0), max_tokens=gen.get("max_tokens", 2000))
        gold = run_readonly_sql(q["gold_sql"], engine, cfg) if q["expect"] == "rows" else None
        passed, why = score(q, ans, gold)
        records.append({**q, "passed": passed, "why": why, "sql": ans.sql, "attempts": ans.attempts,
                        "n_rows": len(ans.rows), "rows": ans.rows[:20], "columns": ans.columns, "answer": ans.text,
                        "cannot_answer": ans.cannot_answer, "reason": ans.reason,
                        "unsupported_numbers": ans.unsupported_numbers, "input_tokens": ans.input_tokens,
                        "output_tokens": ans.output_tokens, "latency_s": round(ans.latency_s, 2)})
        print(f"  {n}/{len(questions)} {'ok  ' if passed else 'FAIL'} {q['id']} {q['question'][:70]}", flush=True)
        time.sleep(args.sleep)

    summary = report(records)
    out = ROOT / "eval/results" / f"sql_eval_{llm.name}.json"
    out.write_text(json.dumps({"backend": llm.name, "model": llm.model, "summary": summary, "records": records}, indent=1))
    print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()