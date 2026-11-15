"""Measure the router and the full graph on questions whose right handling is already known.

    python -m sectra.evaluation.routing_eval                 # routing + entity extraction (LLM calls only)
    python -m sectra.evaluation.routing_eval --retrieval     # also: Recall@5 with the router's filters
    python -m sectra.evaluation.routing_eval --end-to-end    # also: the unanswerable questions through the graph
    python -m sectra.evaluation.routing_eval --limit 20

Questions and their expected handling:
  sql_qa.jsonl                    numeric questions -> "sql"; a few are relabelled below (see SQL_OVERRIDES)
  retrieval_qa_paraphrased.jsonl  82 narrative questions -> "text" (or "both"), with a known ticker and year
                                  15 unanswerable questions -> refused by the router where it can know
  hybrid_qa.jsonl                 15 questions needing a figure and an explanation -> "both"
Results are saved to eval/results/routing_eval_<backend>.json.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from sectra.evaluation.qa_set import load_jsonl

ROOT = Path(__file__).resolve().parents[3]
REFUSE = "refuse"
# sql_qa questions the database cannot answer, labelled by what the ROUTER should do with them.
SQL_OVERRIDES = {
    "sql_39": {REFUSE},            # Apple revenue in fiscal 2005: before the data starts
    "sql_40": {REFUSE},            # stock price
    "sql_41": {"text"},            # iPhone revenue: not a metric, exists only in filing text
    "sql_42": {"text", "sql"},     # quarterly revenue: not in the database; the text may mention it
    "sql_43": {REFUSE},            # forecast
    "sql_44": {REFUSE},            # Tesla: not indexed
    "sql_45": {"text"},            # employee count: only in filing text
    "sql_46": {REFUSE},            # investment advice
}
# Unanswerable questions the router can recognise. The others (odd questions about a real company,
# false premises) look answerable until the evidence is read, so they are judged end to end only.
ROUTER_CAN_REFUSE = {"not_in_corpus", "outside_years", "advice_or_forecast"} | {"un_05"}


def build_items(root: Path = ROOT) -> list[dict]:
    """One list of {id, group, question, accept (set of acceptable outcomes), tickers, fiscal_year, ...}."""
    items = []
    for q in load_jsonl(root / "eval/datasets/sql_qa.jsonl"):
        items.append({"id": q["id"], "group": "numeric", "question": q["question"],
                      "accept": SQL_OVERRIDES.get(q["id"], {"sql"}), "tickers": [], "fiscal_year": None})
    for q in load_jsonl(root / "eval/datasets/retrieval_qa_paraphrased.jsonl"):
        if q["type"] == "unanswerable":
            known = q["category"] in ROUTER_CAN_REFUSE or q["id"] in ROUTER_CAN_REFUSE
            items.append({"id": q["id"], "group": "unanswerable", "question": q["question"], "category": q["category"],
                          "accept": {REFUSE} if known else {REFUSE, "text", "sql", "both"}, "judged_at_router": known,
                          "tickers": [], "fiscal_year": None})
        else:
            items.append({"id": q["id"], "group": "narrative", "question": q["question"], "accept": {"text", "both"},
                          "tickers": [q["ticker"]], "fiscal_year": q["fiscal_year"], "gold_chunk_ids": q["gold_chunk_ids"]})
    for q in load_jsonl(root / "eval/datasets/hybrid_qa.jsonl"):
        items.append({"id": q["id"], "group": "hybrid", "question": q["question"], "accept": {"both"},
                      "tickers": q["tickers"], "fiscal_year": q["fiscal_year"]})
    return items


def outcome(r) -> str:
    return REFUSE if r.refused else r.route


def judge(item: dict, r) -> dict:
    """Compare one routing decision with the expected handling."""
    got = outcome(r)
    rec = {"id": item["id"], "group": item["group"], "question": item["question"], "accept": sorted(item["accept"]),
           "got": got, "route_ok": got in item["accept"], "tickers": r.tickers, "fiscal_years": r.fiscal_years,
           "text_years": r.text_years, "refusal": r.refusal, "fallback": r.fallback, "category": item.get("category"),
           "judged_at_router": item.get("judged_at_router", True)}
    if item["tickers"] and not r.refused:
        rec["tickers_ok"] = all(t in r.tickers for t in item["tickers"])
        if item["group"] == "narrative":
            rec["year_ok"] = r.text_years.get(item["tickers"][0]) == item["fiscal_year"]
    return rec


def summarize(records: list[dict]) -> dict:
    by_group: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["judged_at_router"]:
            by_group[r["group"]].append(r)
    out = {"routing": {}, "outcomes": {}}
    print(f"\n{'group':14} {'n':>4} {'correct':>8} {'accuracy':>9}   outcomes")
    for g in ("numeric", "narrative", "hybrid", "unanswerable"):
        rows = by_group.get(g, [])
        if not rows:
            continue
        ok, got = sum(r["route_ok"] for r in rows), dict(Counter(r["got"] for r in rows).most_common())
        out["routing"][g], out["outcomes"][g] = round(ok / len(rows), 3), got
        print(f"{g:14} {len(rows):>4} {ok:>8} {ok / len(rows):>9.1%}   {got}")
    judged = [r for rows in by_group.values() for r in rows]
    ok = sum(r["route_ok"] for r in judged)
    out["routing"]["all"] = round(ok / len(judged), 3)
    print(f"{'ALL':14} {len(judged):>4} {ok:>8} {ok / len(judged):>9.1%}")

    answerable = [r for r in records if r["group"] != "unanswerable" and "refuse" not in r["accept"]]
    wrongly = [r for r in answerable if r["got"] == REFUSE]
    with_t = [r for r in records if "tickers_ok" in r]
    with_y = [r for r in records if "year_ok" in r]
    out.update(wrongly_refused=len(wrongly), answerable=len(answerable),
               ticker_accuracy=round(sum(r["tickers_ok"] for r in with_t) / len(with_t), 3) if with_t else None,
               year_accuracy=round(sum(r["year_ok"] for r in with_y) / len(with_y), 3) if with_y else None,
               fallbacks=sum(r["fallback"] for r in records))
    print(f"\nanswerable questions wrongly refused: {len(wrongly)} of {len(answerable)}")
    if with_t:
        print(f"company extracted correctly: {sum(r['tickers_ok'] for r in with_t)} of {len(with_t)}")
    if with_y:
        print(f"fiscal year for the text search correct: {sum(r['year_ok'] for r in with_y)} of {len(with_y)}")
    print(f"router replies that could not be parsed: {out['fallbacks']}")

    wrong = [r for r in judged if not r["route_ok"]] + [r for r in records if r.get("tickers_ok") is False or r.get("year_ok") is False]
    seen = set()
    if wrong:
        print("\nto review:")
        for r in wrong:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            why = (f"got {r['got']}, expected {'/'.join(r['accept'])}" if not r["route_ok"] else
                   f"tickers {r['tickers']} years {r['text_years']}")
            print(f"  {r['id']} [{r['group']}] {why}\n      {r['question'][:150]}" + (f"\n      refusal: {r['refusal'][:120]}" if r["refusal"] else ""))
    return out


def recall_with_routed_filters(items: list[dict], routes: dict, retriever, sleep: float) -> dict:
    """Recall@5 on the narrative questions when the router supplies the ticker and year filters."""
    from sectra.evaluation.retrieval_eval import first_gold_rank
    ranks, scoped = [], 0
    narrative = [i for i in items if i["group"] == "narrative"]
    for n, item in enumerate(narrative, start=1):
        r = routes[item["id"]]
        ticker = r.tickers[0] if len(r.tickers) == 1 and not r.refused else None
        year = r.text_years.get(ticker) if ticker else None
        scoped += ticker is not None
        hits = retriever.search_filings(r.text_question or item["question"], ticker=ticker, fiscal_year=year, k=10)
        ranks.append(first_gold_rank(hits, item["gold_chunk_ids"]))
        print(f"\r  retrieval {n}/{len(narrative)}", end="", flush=True)
        time.sleep(sleep)
    n = len(ranks)
    out = {"n": n, "filtered_by_router": scoped,
           "recall@1": round(sum(1 for x in ranks if x and x <= 1) / n, 3),
           "recall@5": round(sum(1 for x in ranks if x and x <= 5) / n, 3),
           "recall@10": round(sum(1 for x in ranks if x) / n, 3),
           "mrr@10": round(sum(1 / x for x in ranks if x) / n, 3)}
    print(f"\n\nretrieval with the router's filters ({scoped} of {n} questions filtered):")
    print(f"  R@1 {out['recall@1']:.1%}   R@5 {out['recall@5']:.1%}   R@10 {out['recall@10']:.1%}   MRR@10 {out['mrr@10']:.3f}")
    return out


def stopped_by(state: dict) -> str:
    """Which layer said no to a question."""
    if not state.get("not_found"):
        return "ANSWERED"
    trace = " | ".join(state.get("trace", []))
    if "refuse:" in trace:
        return "router"
    if "not calling the model" in trace:
        return "no evidence (score gate or SQL declined)"
    return "writer (NOT_FOUND)"


def end_to_end(items: list[dict], graph, sleep: float) -> dict:
    """The unanswerable questions through the whole graph: is every one refused, and by which layer?"""
    rows = []
    unanswerable = [i for i in items if i["group"] == "unanswerable"]
    for n, item in enumerate(unanswerable, start=1):
        state = graph.invoke({"question": item["question"]})
        rows.append({"id": item["id"], "category": item["category"], "question": item["question"],
                     "stopped_by": stopped_by(state), "answer": state.get("answer", "")[:300], "reason": state.get("reason", "")})
        print(f"  {n}/{len(unanswerable)} {rows[-1]['stopped_by']:42} {item['question'][:70]}", flush=True)
        time.sleep(sleep)
    refused = [r for r in rows if r["stopped_by"] != "ANSWERED"]
    print(f"\nunanswerable questions refused end to end: {len(refused)} of {len(rows)}")
    print(f"  by layer: {dict(Counter(r['stopped_by'] for r in rows).most_common())}")
    for r in rows:
        if r["stopped_by"] == "ANSWERED":
            print(f"\n  ANSWERED {r['id']} [{r['category']}] {r['question']}\n    {r['answer'][:250]}")
    return {"n": len(rows), "refused": len(refused), "by_layer": dict(Counter(r["stopped_by"] for r in rows)), "rows": rows}


def main() -> None:  # pragma: no cover - needs services
    from sectra.agents.graph import build_graph, make_deps
    from sectra.agents.router import check_corpus, route

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend")
    p.add_argument("--retrieval", action="store_true")
    p.add_argument("--end-to-end", action="store_true")
    p.add_argument("--limit", type=int)
    p.add_argument("--sleep", type=float, default=1.5, help="seconds between questions (free-tier rate limits)")
    args = p.parse_args()

    deps = make_deps(args.backend)
    items = build_items()[: args.limit]
    print(f"[backend: {deps.llm.name} / {deps.llm.model}]  {len(items)} questions")
    routes, records = {}, []
    for n, item in enumerate(items, start=1):
        r = check_corpus(route(item["question"], deps.llm, deps.catalog, deps.temperature, deps.max_tokens), deps.catalog)
        routes[item["id"]] = r
        records.append(judge(item, r))
        print(f"\r  routing {n}/{len(items)}", end="", flush=True)
        time.sleep(args.sleep)
    print()
    result = {"backend": deps.llm.name, "model": deps.llm.model, "summary": summarize(records), "records": records}
    if args.retrieval:
        result["retrieval"] = recall_with_routed_filters(items, routes, deps.retriever, 0.0)
    if args.end_to_end:
        result["end_to_end"] = end_to_end(items, build_graph(deps), args.sleep)
    out = ROOT / "eval/results" / f"routing_eval_{deps.llm.name}.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()