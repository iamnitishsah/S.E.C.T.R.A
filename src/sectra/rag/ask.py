"""Ask a question about the filings from the command line.

    python -m sectra.rag.ask "What supply chain risks does AMD describe?" --ticker AMD --year 2025 --item 1A
    python -m sectra.rag.ask "..." --backend gemini --show-passages

Every run is appended to data/logs/ask.jsonl (question, filters, chunk ids,
answer, tokens, latency): raw material for the Phase 4 evaluation set.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def log_run(ans, args, backend: str) -> None:
    path = ROOT / "data" / "logs" / "ask.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": ans.question,
        "filters": {"ticker": args.ticker, "fiscal_year": args.year, "item_code": args.item},
        "backend": backend, "model": ans.model,
        "chunk_ids": [p["chunk_id"] for p in ans.passages],
        "scores": [round(p["score"], 4) for p in ans.passages],
        "answer": ans.text, "not_found": ans.not_found, "reason": ans.reason,
        "cited": ans.cited, "invalid_citations": ans.invalid_citations,
        "uncited_sentences": len(ans.uncited_sentences),
        "input_tokens": ans.input_tokens, "output_tokens": ans.output_tokens,
        "latency_s": round(ans.latency_s, 2),
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_answer(ans, show_passages: bool) -> None:
    print("\n" + "=" * 80)
    print(textwrap.fill(ans.text, 100, replace_whitespace=False) if "\n" not in ans.text else ans.text)
    if ans.not_found and ans.reason:
        print(f"\n(reason: {ans.reason})")
    if ans.passages and not ans.not_found:
        print("\nSources:")
        for n, p in enumerate(ans.passages, start=1):
            mark = "*" if n in ans.cited else " "
            print(f" {mark}[{n}] {p['header']}  (score {p['score']:.3f})")
            print(f"       {p['chunk_id']}  {p['source_url']}")
    if ans.invalid_citations:
        print(f"\n!! cites passages that were not provided: {ans.invalid_citations}")
    if ans.uncited_sentences:
        print(f"\n!! {len(ans.uncited_sentences)} sentence(s) without a citation:")
        for s in ans.uncited_sentences[:3]:
            print(f"   - {s[:120]}")
    if ans.model:
        print(f"\n[{ans.model} | {ans.input_tokens} in / {ans.output_tokens} out tokens | {ans.latency_s:.1f}s]")
    if show_passages:
        for n, p in enumerate(ans.passages, start=1):
            print(f"\n--- [{n}] {p['header']}\n{p['text'][:1500]}")


def main() -> None:  # pragma: no cover - needs Qdrant + an API key
    from dotenv import load_dotenv

    from sectra.llm.base import get_llm, load_config
    from sectra.rag.answer import answer
    from sectra.retrieval.dense import DenseRetriever

    p = argparse.ArgumentParser(description="Ask the indexed 10-K filings a question.")
    p.add_argument("question")
    p.add_argument("--ticker")
    p.add_argument("--year", type=int, help="fiscal year, e.g. 2025")
    p.add_argument("--item", help="Item code: 1, 1A, 1C, 3, 7, 7A")
    p.add_argument("--k", type=int, help="passages to retrieve (default from config)")
    p.add_argument("--backend", help="LLM backend from configs/llm.yaml (default: LLM_BACKEND or config)")
    p.add_argument("--show-passages", action="store_true")
    args = p.parse_args()

    load_dotenv(ROOT / ".env")
    rcfg = yaml.safe_load(open(ROOT / "configs" / "retrieval.yaml"))["vector_store"]
    gen = load_config().get("generation", {})
    llm = get_llm(args.backend)
    print(f"[backend: {llm.name} / {llm.model}  (chosen by {llm.source})]")
    ans = answer(args.question, DenseRetriever(), llm, ticker=args.ticker, fiscal_year=args.year,
                 item_code=args.item, k=args.k or rcfg.get("top_k", 5), min_score=rcfg.get("min_score", 0.5),
                 temperature=gen.get("temperature", 0.0), max_tokens=gen.get("max_tokens", 800))
    print_answer(ans, args.show_passages)
    log_run(ans, args, llm.name)


if __name__ == "__main__":
    main()