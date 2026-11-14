"""Tests for the retrieval metrics, with a fake retriever."""

from sectra.evaluation import retrieval_eval as ev


def hit(cid, ticker="AMD", acc="AMD-2025", score=0.7):
    return {"chunk_id": cid, "ticker": ticker, "accession_no": acc, "fiscal_year": 2025, "score": score}


def q(i, gold, qtype="generated"):
    return {"id": f"q{i}", "type": qtype, "question": f"question {i}?", "gold_chunk_ids": gold, "ticker": "AMD",
            "fiscal_year": 2025, "accession_no": "AMD-2025", "item_code": "1A", "word_overlap": 0.4}


class FakeRetriever:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def search_filings(self, query, k=10, **filters):
        self.calls.append(filters)
        return self.answers[query][:k]


def test_metrics():
    questions = [q(1, ["a"]), q(2, ["b", "b2"]), q(3, ["c"]), q(4, ["d"]), q(5, [], "unanswerable")]
    answers = {
        "question 1?": [hit("a")],                                              # rank 1
        "question 2?": [hit("x"), hit("y"), hit("b2")],                         # rank 3 via an alternate gold chunk
        "question 3?": [hit(f"n{i}") for i in range(6)] + [hit("c")],           # rank 7: found at 10, not at 5
        "question 4?": [hit("z", ticker="NVDA", acc="NVDA-2025")],              # never found
        "question 5?": [hit("u", score=0.55)],
    }
    rows = ev.run_setting(questions, FakeRetriever(answers), "open")
    m = ev.summarize(rows)
    assert m == {"n": 4, "recall@1": 0.25, "recall@5": 0.5, "recall@10": 0.75, "mrr@10": round((1 + 1/3 + 1/7) / 4, 3)}
    by = {r["id"]: r for r in rows}
    assert by["q3"]["miss"] == "right filing, wrong passage" and by["q4"]["miss"] == "wrong company"
    assert "rank" not in by["q5"] and by["q5"]["top1_score"] == 0.55


def test_wrong_year_miss_and_filters():
    questions = [q(1, ["a"])]
    r = FakeRetriever({"question 1?": [hit("old", acc="AMD-2024")]})
    rows = ev.run_setting(questions, r, "scoped")
    assert rows[0]["miss"] == "right company, wrong year"
    assert r.calls == [{"ticker": "AMD", "fiscal_year": 2025}]
    ev.run_setting(questions, r, "open")
    assert r.calls[-1] == {}


def test_report_runs(capsys):
    questions = [q(1, ["a"]), q(2, [], "unanswerable")]
    r = FakeRetriever({"question 1?": [hit("a")], "question 2?": []})
    results = {s: ev.run_setting(questions, r, s) for s in ("open", "scoped")}
    summary = ev.report("dense", questions, results)
    assert summary["open"]["recall@5"] == 1.0 and "none retrieved" in capsys.readouterr().out


def test_compare_and_sign_test(tmp_path, capsys):
    import json
    res = tmp_path / "eval/results"
    res.mkdir(parents=True)

    def save(variant, ranks):
        rows = [{"id": f"q{i}", "type": "generated", "rank": r} for i, r in enumerate(ranks)]
        both = {"open": rows, "scoped": rows}
        res.joinpath(f"retrieval_{variant}.json").write_text(
            json.dumps({"summary": {s: ev.summarize(rows) for s in both}, "results": both}))

    save("dense", [1, None, 7, 3])
    save("rerank", [1, 2, 4, None])
    ev.compare(tmp_path, ["dense", "rerank"])
    assert "gained 2 questions, lost 1" in capsys.readouterr().out
    assert ev.sign_test(0, 0) == 1.0 and ev.sign_test(5, 5) == 1.0
    assert abs(ev.sign_test(10, 0) - 2 / 2 ** 10) < 1e-12
