"""Build the retrieval evaluation set (eval/datasets/retrieval_qa.jsonl).

    python -m sectra.evaluation.qa_set generate          # an LLM writes one question per sampled chunk
    python -m sectra.evaluation.qa_set review            # keep / reject pending candidates by hand
    python -m sectra.evaluation.qa_set review --recheck 30   # hand-check 30 verdicts made by an LLM reviewer
    python -m sectra.evaluation.qa_set build             # kept + handwritten + unanswerable -> retrieval_qa.jsonl

How gold labels work: each generated question comes with an exact quote from its
source chunk. Gold = every chunk of the same filing that contains that quote
(neighbouring chunks overlap, so more than one can hold the answer). Because gold
is derived from the quote, it can be recomputed if the chunking rules change.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import textwrap
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ITEM_PLAN = ["1A", "1A", "7", "7", "other"]          # per company: 2 risk, 2 MD&A, 1 from the rest
OTHER_ITEMS = ("1", "1C", "3", "7A")
STOPWORDS = set("""a an and are as at be by company companys did does for from fiscal has have how in is it its
of on or that the their this to was were what when which who why with year say said describe described""".split())

SYSTEM_PROMPT = """You write evaluation questions for a search system over SEC 10-K filings.
You are given one passage. Write ONE question that this passage answers.

Rules:
1. The question must stand alone: name the company and the fiscal year, e.g. "In fiscal 2025, what did AMD say about ...?".
2. Ask about something specific to this passage. Not a generic question ("What risks does the company face?") that many passages could answer.
3. Use your own words. Do not copy any phrase of more than three words from the passage.
4. "answer_quote": copy ONE contiguous span of at most 40 words from the passage, character for character, that contains the answer.
5. "answer": the answer in one sentence.
6. If the passage is boilerplate, a list of headings, or has no specific fact to ask about, return {"skip": true}.

Return only JSON: {"question": "...", "answer": "...", "answer_quote": "..."}"""


PARAPHRASE_PROMPT = """You rewrite questions about SEC 10-K filings so they keep their meaning but use different words.

Rules:
1. Keep the company name and the fiscal year exactly as they are.
2. Keep proper nouns, product and drug names, names of laws, and numbers.
3. Rephrase everything else the way another analyst would ask the same thing. Avoid the words listed under "Avoid" wherever a natural alternative exists.
4. The answer to the question must stay the same.
5. One question, one sentence.

Return only JSON: {"question": "..."}"""


# ------------------------------------------------------------------ helpers

HYPHENS = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")   # gpt-oss writes U+2011


def norm(s: str) -> str:
    """Lowercase, plain hyphens and quotes, single spaces: so quotes can be matched reliably."""
    s = s.translate(HYPHENS)
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().lower()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with open(tmp, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def table_share(text: str) -> float:
    lines, in_table, n_table = text.split("\n"), False, 0
    for line in lines:
        if line == "[TABLE]":
            in_table = True
        n_table += in_table
        if line == "[/TABLE]":
            in_table = False
    return n_table / max(len(lines), 1)


def eligible(chunk: dict) -> bool:
    """Enough prose to ask a real question about."""
    return chunk["n_tokens"] >= 150 and table_share(chunk["text"]) < 0.5


def word_overlap(question: str, passage: str) -> float:
    """Share of the question's content words that also appear in the passage (high = likely copied)."""
    words = {w for w in re.findall(r"[a-z]{4,}", norm(question)) if w not in STOPWORDS}
    passage_words = set(re.findall(r"[a-z]{4,}", norm(passage)))
    return round(len(words & passage_words) / max(len(words), 1), 2)


def find_gold(quote: str, filing_chunks: list[dict]) -> list[str]:
    q = norm(quote).rstrip(".,;: ")          # models often end a quote with a full stop of their own
    return [c["chunk_id"] for c in filing_chunks if q and q in norm(c["text"])]


def parse_json(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# ----------------------------------------------------------------- sampling

def sample_chunks(chunks: list[dict], per_ticker: int = 5, seed: int = 7) -> list[dict]:
    """Same number of chunks per company, spread over Items by ITEM_PLAN. Deterministic for a seed."""
    rng = random.Random(seed)
    pools: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for c in chunks:
        if not eligible(c):
            continue
        slot = c["item_code"] if c["item_code"] in ("1A", "7") else "other" if c["item_code"] in OTHER_ITEMS else None
        if slot:
            pools[c["ticker"]][slot].append(c)

    picked = []
    for ticker in sorted(pools):
        used: set[str] = set()
        plan = (ITEM_PLAN * (per_ticker // len(ITEM_PLAN) + 1))[:per_ticker]
        for slot in plan:
            pool = [c for c in pools[ticker][slot] if c["chunk_id"] not in used]
            if not pool:                                  # this company has none left for the slot
                pool = [c for s in pools[ticker].values() for c in s if c["chunk_id"] not in used]
            if pool:
                c = rng.choice(pool)
                used.add(c["chunk_id"])
                picked.append(c)
    return picked


# --------------------------------------------------------------- generation

def generate_one(chunk: dict, filing_chunks: list[dict], llm, company_name: str = "") -> dict:
    """Ask the LLM for one question about this chunk, then check what it returned."""
    base = {
        "id": f"gen_{chunk['chunk_id']}", "type": "generated", "source_chunk_id": chunk["chunk_id"],
        "accession_no": chunk["accession_no"], "ticker": chunk["ticker"],
        "fiscal_year": chunk["fiscal_year"], "item_code": chunk["item_code"],
        "header": chunk["header"], "passage": chunk["text"],
    }
    who = f"Company: {company_name} ({chunk['ticker']})\n" if company_name else ""
    user = f"{who}Passage source: {chunk['header']}\n\n<passage>\n{chunk['text']}\n</passage>"
    resp = llm.complete(SYSTEM_PROMPT, user, temperature=0.2, max_tokens=1500)
    data = parse_json(resp.text)

    if data is None:
        return {**base, "status": "invalid", "review_note": "LLM did not return JSON"}
    if data.get("skip"):
        return {**base, "status": "skipped", "review_note": "LLM: nothing specific to ask"}
    question, quote = str(data.get("question", "")).strip(), str(data.get("answer_quote", "")).strip()
    rec = {**base, "question": question, "answer": str(data.get("answer", "")).strip(),
           "answer_quote": quote, "word_overlap": word_overlap(question, chunk["text"]),
           "generator": resp.model}

    gold = find_gold(quote, filing_chunks)
    problems = []
    if not question.endswith("?"):
        problems.append("not a question")
    if str(chunk["fiscal_year"]) not in question:
        problems.append("fiscal year missing from question")
    if not gold:
        problems.append("quote not found in passage")
    if len(quote.split()) > 60:
        problems.append("quote too long")
    if problems:
        return {**rec, "status": "invalid", "review_note": "; ".join(problems)}
    return {**rec, "gold_chunk_ids": gold, "status": "pending"}


def company_names(root: Path) -> dict[str, str]:
    path = root / "data" / "raw" / "manifest" / "companies.csv"
    if not path.exists():
        return {}
    with open(path, newline="") as fh:
        return {r["ticker"]: r["name"] for r in csv.DictReader(fh)}


def cmd_generate(root: Path, llm, per_ticker: int = 5, seed: int = 7, sleep: float = 2.0, limit: int | None = None) -> None:
    chunks = load_jsonl(root / "data/processed/chunks/chunks.jsonl")
    by_filing = defaultdict(list)
    for c in chunks:
        by_filing[c["accession_no"]].append(c)
    names = company_names(root)
    out = root / "eval/datasets/candidates.jsonl"
    done = {r["source_chunk_id"] for r in load_jsonl(out)}       # resume: never ask twice for a chunk

    todo = [c for c in sample_chunks(chunks, per_ticker, seed) if c["chunk_id"] not in done][:limit]
    print(f"{len(done)} candidates already generated, {len(todo)} to go")
    out.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    for i, chunk in enumerate(todo, 1):
        try:
            rec = generate_one(chunk, by_filing[chunk["accession_no"]], llm, names.get(chunk["ticker"], ""))
        except Exception as exc:                                  # rate limit etc.: stop, resume later
            print(f"stopped at {i}/{len(todo)}: {exc!r}\nRun the same command again to resume.")
            break
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        counts[rec["status"]] += 1
        print(f"[{i}/{len(todo)}] {chunk['ticker']} FY{chunk['fiscal_year']} Item {chunk['item_code']:2}  "
              f"{rec['status']:8} {rec.get('question', rec.get('review_note', ''))[:90]}")
        time.sleep(sleep)
    print(f"this run: {dict(counts)} -> {out.relative_to(root)}")


# ------------------------------------------------------------------- review

def show(rec: dict) -> None:
    print("\n" + "=" * 100)
    print(f"{rec['id']}   [{rec['status']}]   word overlap {rec.get('word_overlap')}")
    if rec.get("review_note"):
        print(f"note ({rec.get('reviewer', '-')}): {rec['review_note']}")
    print(f"\nQ: {rec['question']}\nA: {rec['answer']}\nQuote: \"{rec['answer_quote']}\"\n")
    print(rec["header"])
    print(textwrap.indent(textwrap.shorten(rec["passage"].replace("\n", " / "), 1400), "  | "))


def cmd_review(root: Path, recheck: int = 0, seed: int = 11, ask=input) -> None:
    path = root / "eval/datasets/candidates.jsonl"
    rows = load_jsonl(path)
    if recheck:        # hand-check verdicts that were not made by a human
        pool = [r for r in rows if r["status"] in ("keep", "reject") and r.get("reviewer") != "human"]
        queue = random.Random(seed).sample(pool, min(recheck, len(pool)))
    else:
        queue = [r for r in rows if r["status"] == "pending"]
    print(f"{len(queue)} to review.  k = keep, r = reject, e = edit question then keep, s = skip, q = quit")

    agreed = judged = 0
    for rec in queue:
        show(rec)
        choice = ask("k / r / e / s / q > ").strip().lower()
        if choice == "q":
            break
        if choice == "e":
            new_q = ask("new question > ").strip()
            if new_q:
                rec["question"], rec["word_overlap"] = new_q, word_overlap(new_q, rec["passage"])
            choice = "k"
        if choice not in ("k", "r"):
            continue
        verdict = "keep" if choice == "k" else "reject"
        if recheck:
            judged += 1
            agreed += verdict == rec["status"]
            rec["previous_verdict"] = f"{rec['status']} by {rec.get('reviewer', '?')}"
        rec["status"], rec["reviewer"] = verdict, "human"
        write_jsonl(path, rows)                                   # save after every decision
    if recheck and judged:
        print(f"\nYou agreed with {agreed} of {judged} earlier verdicts ({agreed / judged:.0%}).")
    print("status now:", dict(Counter(r["status"] for r in rows)))


# -------------------------------------------------------------------- build

def cmd_build(root: Path) -> list[dict]:
    ds = root / "eval/datasets"
    chunks = load_jsonl(root / "data/processed/chunks/chunks.jsonl")
    ids = {c["chunk_id"] for c in chunks}
    by_filing = defaultdict(list)
    for c in chunks:
        by_filing[c["accession_no"]].append(c)

    out, dropped = [], []
    for r in load_jsonl(ds / "candidates.jsonl"):
        if r["status"] != "keep":
            continue
        gold = find_gold(r["answer_quote"], by_filing[r["accession_no"]])   # recomputed: survives re-chunking
        if not gold:
            dropped.append(r["id"])
            continue
        out.append({k: r.get(k) for k in ("id", "type", "question", "answer", "answer_quote", "accession_no",
                                         "ticker", "fiscal_year", "item_code", "word_overlap", "reviewer")} | {"gold_chunk_ids": gold})
    for r in load_jsonl(ds / "handwritten.jsonl"):
        missing = [g for g in r["gold_chunk_ids"] if g not in ids]
        if missing:
            dropped.append(r["id"])
            continue
        out.append({**r, "type": "handwritten"})
    for r in load_jsonl(ds / "unanswerable.jsonl"):
        out.append({**r, "type": "unanswerable", "gold_chunk_ids": []})

    if len({r["id"] for r in out}) != len(out):
        raise SystemExit("duplicate ids in the evaluation set")
    write_jsonl(ds / "retrieval_qa.jsonl", out)
    print(f"{len(out)} questions -> eval/datasets/retrieval_qa.jsonl")
    print("  by type:  ", dict(Counter(r["type"] for r in out)))
    answerable = [r for r in out if r["type"] != "unanswerable"]
    print("  by item:  ", dict(sorted(Counter(r.get("item_code") for r in answerable).items(), key=str)))
    print("  by ticker:", dict(sorted(Counter(r.get("ticker") for r in answerable).items(), key=str)))
    if dropped:
        print(f"  dropped (gold chunk no longer exists): {dropped}")
    return out


# --------------------------------------------------------------- paraphrase

def cmd_paraphrase(root: Path, llm, sleep: float = 4.0) -> None:
    """Rewrite every answerable question in different words; gold chunks stay the same."""
    ds = root / "eval/datasets"
    questions = load_jsonl(ds / "retrieval_qa.jsonl")
    passages = {r["id"]: r["passage"] for r in load_jsonl(ds / "candidates.jsonl")}
    out = ds / "retrieval_qa_paraphrased.jsonl"
    done = {r["id"] for r in load_jsonl(out)}
    todo = [q for q in questions if q["id"] not in done]
    print(f"{len(done)} already done, {len(todo)} to go")

    for i, q in enumerate(todo, 1):
        rec = dict(q)
        passage = passages.get(q["id"])
        if q["type"] != "unanswerable" and passage:
            shared = sorted({w for w in re.findall(r"[a-z]{4,}", norm(q["question"])) if w not in STOPWORDS}
                            & set(re.findall(r"[a-z]{4,}", norm(passage))))
            user = (f"Question: {q['question']}\n"
                    f"Answer (context only, do not include it): {q.get('answer', '')}\n"
                    f"Avoid: {', '.join(shared)}")
            try:
                resp = llm.complete(PARAPHRASE_PROMPT, user, temperature=0.3, max_tokens=1500)
            except Exception as exc:                              # rate limit etc.: stop, resume later
                print(f"stopped at {i}/{len(todo)}: {exc!r}\nRun the same command again to resume.")
                break
            new_q = str((parse_json(resp.text) or {}).get("question", "")).strip()
            ok = new_q.endswith("?") and str(q["fiscal_year"]) in new_q
            if ok:
                rec.update(question=new_q, original_question=q["question"],
                           original_word_overlap=q.get("word_overlap"),
                           word_overlap=word_overlap(new_q, passage), paraphraser=resp.model)
            rec["paraphrased"] = ok
            print(f"[{i}/{len(todo)}] overlap {q.get('word_overlap')} -> {rec['word_overlap']}  "
                  f"{'ok  ' if ok else 'KEPT ORIGINAL'}  {rec['question'][:100]}")
            time.sleep(sleep)
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    rows = [r for r in load_jsonl(out) if r["type"] != "unanswerable"]
    if rows:
        before = sorted(r.get("original_word_overlap", r.get("word_overlap")) for r in rows)
        after = sorted(r["word_overlap"] for r in rows)
        print(f"{len(rows)} answerable questions | {sum(r.get('paraphrased', False) for r in rows)} paraphrased | "
              f"median word overlap {before[len(before) // 2]} -> {after[len(after) // 2]} | "
              f"low-overlap (<=0.5): {sum(o <= 0.5 for o in after)}")


def main() -> None:  # pragma: no cover
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--per-ticker", type=int, default=5)
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--sleep", type=float, default=2.0, help="seconds between LLM calls (free-tier rate limits)")
    g.add_argument("--limit", type=int, help="generate at most this many in this run")
    g.add_argument("--backend")
    r = sub.add_parser("review")
    r.add_argument("--recheck", type=int, default=0, help="hand-check N verdicts made by a non-human reviewer")
    sub.add_parser("build")
    pp = sub.add_parser("paraphrase")
    pp.add_argument("--backend")
    pp.add_argument("--sleep", type=float, default=4.0)
    args = p.parse_args()

    if args.cmd in ("generate", "paraphrase"):
        from dotenv import load_dotenv

        from sectra.llm.base import get_llm
        load_dotenv(ROOT / ".env")
        llm = get_llm(args.backend)
        print(f"[backend: {llm.name} / {llm.model}]")
        if args.cmd == "generate":
            cmd_generate(ROOT, llm, args.per_ticker, args.seed, args.sleep, args.limit)
        else:
            cmd_paraphrase(ROOT, llm, args.sleep)
    elif args.cmd == "review":
        cmd_review(ROOT, args.recheck)
    else:
        cmd_build(ROOT)


if __name__ == "__main__":
    main()
