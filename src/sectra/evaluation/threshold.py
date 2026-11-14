"""Pick the refusal threshold for the top-1 retrieval score from saved eval results.

    python -m sectra.evaluation.threshold --variant rerank
    python -m sectra.evaluation.threshold --variant dense --max-loss 0.05

For each candidate threshold (just above each unanswerable question's score):
  stopped  unanswerable questions refused before the LLM is called
  lost     answerable questions refused although the gold passage was in the top 5
The suggested threshold is the highest one that loses at most --max-loss of the
answerable questions on the paraphrased set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sectra.evaluation.qa_set import load_jsonl
from sectra.evaluation.retrieval_eval import result_path

ROOT = Path(__file__).resolve().parents[3]
SETS = ("original", "paraphrased")


def split_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    ans = [r for r in rows if r["type"] != "unanswerable" and r["top1_score"] is not None]
    unans = [r for r in rows if r["type"] == "unanswerable" and r["top1_score"] is not None]
    return ans, unans


def lost(ans: list[dict], thr: float) -> int:
    return sum(1 for r in ans if r["top1_score"] < thr and r.get("rank") and r["rank"] <= 5)


def sweep(answerable: dict[str, list[dict]], unans: list[dict]) -> list[dict]:
    cuts = sorted({0.0} | {round(r["top1_score"] + 1e-4, 4) for r in unans})
    return [{"threshold": t,
             "stopped": sum(1 for r in unans if r["top1_score"] < t),
             "lost": {name: lost(rows, t) for name, rows in answerable.items()}} for t in cuts]


def suggest(table: list[dict], n_main: int, main: str, max_loss: float) -> float:
    ok = [row["threshold"] for row in table if row["lost"][main] <= max_loss * n_main]
    return max(ok) if ok else 0.0


def main() -> None:  # pragma: no cover - reads saved result files
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variant", default="rerank")
    p.add_argument("--setting", default="open", choices=("open", "scoped"))
    p.add_argument("--max-loss", type=float, default=0.02)
    args = p.parse_args()

    answerable, unans = {}, []
    for name in SETS:
        rows = json.loads(result_path(ROOT, args.variant, name).read_text())["results"][args.setting]
        answerable[name], u = split_rows(rows)
        unans = unans or u                      # the unanswerable questions are the same in both sets

    table = sweep(answerable, unans)
    n = {name: len(rows) for name, rows in answerable.items()}
    pick = suggest(table, n["paraphrased"], "paraphrased", args.max_loss)

    print(f"variant: {args.variant} | setting: {args.setting} | unanswerable: {len(unans)}")
    print(f"{'threshold':>9}  {'stopped':>9}  " + "  ".join(f"lost ({s}, n={n[s]})" for s in SETS))
    for row in table:
        mark = "  <- suggested" if row["threshold"] == pick else ""
        cells = "  ".join(f"{row['lost'][s]:>3} ({row['lost'][s] / n[s]:>5.1%})".ljust(len(f"lost ({s}, n={n[s]})"))
                          for s in SETS)
        print(f"{row['threshold']:>9.4f}  {row['stopped']:>4} / {len(unans):<2}  {cells}{mark}")

    info = {q["id"]: q for q in load_jsonl(ROOT / "eval/datasets/retrieval_qa.jsonl")}
    passing = sorted((r for r in unans if r["top1_score"] >= pick), key=lambda r: -r["top1_score"])
    print(f"\nunanswerable questions that still reach the LLM at {pick:.4f} ({len(passing)}):")
    for r in passing:
        q = info.get(r["id"], {})
        print(f"  {r['top1_score']:.3f}  [{q.get('category', '?')}] {q.get('question', r['id'])[:90]}")


if __name__ == "__main__":
    main()