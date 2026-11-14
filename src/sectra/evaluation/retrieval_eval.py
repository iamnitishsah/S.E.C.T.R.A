"""Measure retrieval quality on eval/datasets/retrieval_qa.jsonl.

    python -m sectra.evaluation.retrieval_eval                  # dense baseline
    python -m sectra.evaluation.retrieval_eval --variant dense

Each variant is run in two settings:
  open    no filters: search every chunk (the question itself names company and year)
  scoped  ticker + fiscal year passed as filters (what the agent will do in Phase 6)

A question counts as found at k if ANY of its gold chunks is in the top k.
  Recall@5, Recall@10   share of questions found in the top 5 / 10
  MRR@10                mean of 1/rank of the first gold chunk (0 if not in the top 10)
Results are saved per question, so later variants can be compared question by question.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from sectra.evaluation.qa_set import load_jsonl

ROOT = Path(__file__).resolve().parents[3]
K = 10


def make_retriever(variant: str):
    """Variants are added here as they are built (hybrid, rerank...)."""
    if variant == "dense":
        from sectra.retrieval.dense import DenseRetriever
        return DenseRetriever()
    raise SystemExit(f"unknown variant {variant!r}")


def first_gold_rank(hits: list[dict], gold: list[str]) -> int | None:
    for rank, h in enumerate(hits, start=1):
        if h["chunk_id"] in gold:
            return rank
    return None


def miss_type(hits: list[dict], q: dict) -> str:
    """Why was the gold chunk not in the top 5?"""
    top = hits[:5]
    if any(h["accession_no"] == q["accession_no"] for h in top):
        return "right filing, wrong passage"
    if any(h["ticker"] == q["ticker"] for h in top):
        return "right company, wrong year"
    return "wrong company"


def run_setting(questions: list[dict], retriever, setting: str) -> list[dict]:
    rows = []
    for q in questions:
        filters = {"ticker": q.get("ticker"), "fiscal_year": q.get("fiscal_year")} if setting == "scoped" else {}
        hits = retriever.search_filings(q["question"], k=K, **filters)
        row = {"id": q["id"], "type": q["type"], "top1_score": round(hits[0]["score"], 4) if hits else None,
               "retrieved": [h["chunk_id"] for h in hits]}
        if q["type"] != "unanswerable":
            rank = first_gold_rank(hits, q["gold_chunk_ids"])
            row["rank"] = rank
            if rank is None or rank > 5:
                row["miss"] = miss_type(hits, q)
        rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    ranks = [r["rank"] for r in rows if r["type"] != "unanswerable"]
    n = len(ranks)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "recall@1": round(sum(r == 1 for r in ranks if r) / n, 3),
        "recall@5": round(sum(r <= 5 for r in ranks if r) / n, 3),
        "recall@10": round(sum(r <= 10 for r in ranks if r) / n, 3),
        "mrr@10": round(sum(1 / r for r in ranks if r) / n, 3),
    }


def score_stats(scores: list[float]) -> str:
    scores = sorted(s for s in scores if s is not None)
    if not scores:
        return "none retrieved"
    return f"min {scores[0]:.3f}  median {statistics.median(scores):.3f}  max {scores[-1]:.3f}  (n={len(scores)})"


def report(variant: str, questions: list[dict], results: dict[str, list[dict]]) -> dict:
    by_id = {q["id"]: q for q in questions}
    summary = {s: summarize(rows) for s, rows in results.items()}
    print(f"\nvariant: {variant}")
    print(f"{'setting':8} {'n':>4} {'R@1':>7} {'R@5':>7} {'R@10':>7} {'MRR@10':>7}")
    for s, m in summary.items():
        print(f"{s:8} {m['n']:>4} {m['recall@1']:>7.1%} {m['recall@5']:>7.1%} {m['recall@10']:>7.1%} {m['mrr@10']:>7.3f}")

    open_rows = [r for r in results["open"] if r["type"] != "unanswerable"]

    def group(label, key):
        print(f"\nopen setting by {label}:")
        buckets: dict[str, list[dict]] = {}
        for r in open_rows:
            buckets.setdefault(key(by_id[r["id"]]), []).append(r)
        for name in sorted(buckets):
            m = summarize(buckets[name])
            print(f"  {name:22} n={m['n']:>3}  R@5 {m['recall@5']:>6.1%}  MRR {m['mrr@10']:.3f}")

    group("Item", lambda q: q["item_code"] if q["item_code"] in ("1A", "7") else "other")
    group("question/passage word overlap",
          lambda q: "n/a" if q.get("word_overlap") is None else
          "low (<=0.5)" if q["word_overlap"] <= 0.5 else "high (>=0.8)" if q["word_overlap"] >= 0.8 else "medium")

    misses = Counter(r["miss"] for r in open_rows if "miss" in r)
    print(f"\nopen setting, not in top 5 ({sum(misses.values())} questions): {dict(misses)}")

    print("\ntop-1 score, open setting (for the refusal threshold in step 4.5):")
    print("  answerable:  ", score_stats([r["top1_score"] for r in open_rows]))
    print("  unanswerable:", score_stats([r["top1_score"] for r in results["open"] if r["type"] == "unanswerable"]))
    return summary


def main() -> None:  # pragma: no cover - needs Qdrant
    from dotenv import load_dotenv

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variant", default="dense")
    args = p.parse_args()
    load_dotenv(ROOT / ".env")

    questions = load_jsonl(ROOT / "eval/datasets/retrieval_qa.jsonl")
    retriever = make_retriever(args.variant)
    results = {s: run_setting(questions, retriever, s) for s in ("open", "scoped")}
    summary = report(args.variant, questions, results)

    out = ROOT / "eval/results" / f"retrieval_{args.variant}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"variant": args.variant, "k": K, "summary": summary, "results": results}, indent=1))
    print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
