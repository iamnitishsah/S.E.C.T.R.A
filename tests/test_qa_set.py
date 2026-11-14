"""Tests for the evaluation-set builder, with a fake LLM and a temporary project folder."""

import json

from sectra.evaluation import qa_set
from sectra.llm.base import LLMResponse

PROSE = "We rely on a single foundry in Taiwan for all leading edge wafers. " * 12


def chunk(ticker, year, item, seq, text=PROSE, n_tokens=300):
    acc = f"{ticker}-{year}"
    return {"chunk_id": f"{acc}_{item}_{seq:03d}", "accession_no": acc, "ticker": ticker, "fiscal_year": year,
            "item_code": item, "header": f"{ticker} 10-K FY{year} | Item {item}", "text": text, "n_tokens": n_tokens}


def corpus():
    rows = []
    for t in ("AMD", "NVDA", "PFE"):
        for y in (2024, 2025):
            for item in ("1", "1A", "1C", "7", "7A"):
                rows += [chunk(t, y, item, s, text=f"{t} {y} {item} part {s}. " + PROSE) for s in range(6)]
    return rows


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.calls = reply, 0

    def complete(self, system, user, temperature=0.0, max_tokens=800):
        self.calls += 1
        text = self.reply(user) if callable(self.reply) else self.reply
        return LLMResponse(text, "fake", 10, 10, 0.0)


def good_reply(user):
    year = "2025" if "FY2025" in user else "2024"
    return json.dumps({"question": f"In fiscal {year}, where does the firm get its most advanced chips made?",
                       "answer": "At one foundry in Taiwan.",
                       "answer_quote": "rely on a single foundry in Taiwan for all leading edge wafers"})


def project(tmp_path, chunks):
    d = tmp_path / "data/processed/chunks"
    d.mkdir(parents=True)
    qa_set.write_jsonl(d / "chunks.jsonl", chunks)
    return tmp_path


def test_sampling_is_balanced_and_deterministic():
    a, b = qa_set.sample_chunks(corpus(), per_ticker=5, seed=7), qa_set.sample_chunks(corpus(), per_ticker=5, seed=7)
    assert [c["chunk_id"] for c in a] == [c["chunk_id"] for c in b]
    assert len(a) == 15 and len({c["chunk_id"] for c in a}) == 15
    for t in ("AMD", "NVDA", "PFE"):
        items = [c["item_code"] for c in a if c["ticker"] == t]
        assert items.count("1A") == 2 and items.count("7") == 2 and len(items) == 5


def test_ineligible_chunks_are_not_sampled():
    table = "[TABLE]\n" + "\n".join(f"Row {i} | 1 | 2" for i in range(30)) + "\n[/TABLE]"
    rows = [chunk("AMD", 2025, "7", 0, text=table), chunk("AMD", 2025, "7", 1, n_tokens=40), chunk("AMD", 2025, "7", 2)]
    assert [c["chunk_id"] for c in qa_set.sample_chunks(rows, per_ticker=5)] == ["AMD-2025_7_002"]


def test_generate_one_accepts_valid_and_finds_overlapping_gold():
    a, b = chunk("AMD", 2025, "1A", 0), chunk("AMD", 2025, "1A", 1)      # both contain the quote (overlap)
    rec = qa_set.generate_one(a, [a, b, chunk("AMD", 2025, "7", 0, text="Unrelated text.")], FakeLLM(good_reply))
    assert rec["status"] == "pending" and rec["gold_chunk_ids"] == [a["chunk_id"], b["chunk_id"]]
    assert rec["id"] == "gen_AMD-2025_1A_000" and 0 <= rec["word_overlap"] <= 1


def test_generate_one_rejects_bad_output():
    c = chunk("AMD", 2025, "1A", 0)
    def run(reply):
        return qa_set.generate_one(c, [c], FakeLLM(reply))
    assert run("no json here")["status"] == "invalid"
    assert run('{"skip": true}')["status"] == "skipped"
    no_year = run(json.dumps({"question": "Where are chips made?", "answer": "x", "answer_quote": "single foundry in Taiwan"}))
    assert no_year["status"] == "invalid" and "fiscal year" in no_year["review_note"]
    bad_quote = run(json.dumps({"question": "In fiscal 2025, where are chips made?", "answer": "x", "answer_quote": "a fab in Arizona"}))
    assert bad_quote["status"] == "invalid" and "quote not found" in bad_quote["review_note"]


def test_quote_matching_ignores_curly_quotes_and_spacing():
    c = chunk("AMD", 2025, "1A", 0, text="The company’s  products\nrely on TSMC.")
    assert qa_set.find_gold("company's products rely on TSMC", [c]) == [c["chunk_id"]]


def test_quote_matching_ignores_unicode_hyphens_and_added_full_stop():
    c = chunk("QCOM", 2026, "1A", 0, text="We depend on third-party suppliers for wafers, and for certain IP.")
    assert qa_set.find_gold("We depend on third\u2011party suppliers for wafers.", [c]) == [c["chunk_id"]]


def test_generate_resumes_without_repeating(tmp_path):
    root = project(tmp_path, corpus())
    llm = FakeLLM(good_reply)
    qa_set.cmd_generate(root, llm, per_ticker=5, sleep=0, limit=4)
    qa_set.cmd_generate(root, llm, per_ticker=5, sleep=0)
    rows = qa_set.load_jsonl(root / "eval/datasets/candidates.jsonl")
    assert len(rows) == 15 and llm.calls == 15 and len({r["source_chunk_id"] for r in rows}) == 15


def test_review_recheck_and_build(tmp_path):
    root = project(tmp_path, corpus())
    qa_set.cmd_generate(root, FakeLLM(good_reply), per_ticker=5, sleep=0)
    path = root / "eval/datasets/candidates.jsonl"

    answers = iter(["k", "r", "e", "In fiscal 2025, who fabricates the most advanced chips?", "s", "q"])
    qa_set.cmd_review(root, ask=lambda _: next(answers))
    rows = qa_set.load_jsonl(path)
    assert [r["status"] for r in rows[:4]] == ["keep", "reject", "keep", "pending"]
    assert rows[2]["question"].startswith("In fiscal 2025, who fabricates") and rows[0]["reviewer"] == "human"

    for r in rows[3:]:                                   # an LLM reviewer's verdicts
        r["status"], r["reviewer"] = "keep", "claude"
    qa_set.write_jsonl(path, rows)
    qa_set.cmd_review(root, recheck=3, ask=lambda _: "r")
    rows = qa_set.load_jsonl(path)
    assert sum(r.get("previous_verdict") == "keep by claude" for r in rows) == 3

    ds = root / "eval/datasets"
    qa_set.write_jsonl(ds / "unanswerable.jsonl", [{"id": "un_01", "question": "Cafeteria menu?", "category": "off_topic"}])
    qa_set.write_jsonl(ds / "handwritten.jsonl", [
        {"id": "hw_01", "question": "q?", "gold_chunk_ids": ["AMD-2025_7_000"]},
        {"id": "hw_02", "question": "q?", "gold_chunk_ids": ["does-not-exist"]}])
    out = qa_set.cmd_build(root)
    kept = sum(r["status"] == "keep" for r in rows)
    types = [r["type"] for r in out]
    assert types.count("generated") == kept and types.count("handwritten") == 1 and types.count("unanswerable") == 1
    assert all(r["gold_chunk_ids"] for r in out if r["type"] == "generated")
