"""Tests for the routing evaluation: the question list and the scoring (no services)."""

from collections import Counter

from sectra.agents.router import Route
from sectra.evaluation.routing_eval import build_items, judge, outcome, stopped_by, summarize


def test_items_cover_every_group_with_expected_handling():
    items = build_items()
    assert Counter(i["group"] for i in items) == {"numeric": 46, "narrative": 82, "unanswerable": 15, "hybrid": 15}
    by_id = {i["id"]: i for i in items}
    assert by_id["sql_01"]["accept"] == {"sql"} and by_id["sql_44"]["accept"] == {"refuse"} and by_id["sql_41"]["accept"] == {"text"}
    assert by_id["un_06"]["accept"] == {"refuse"} and by_id["un_06"]["judged_at_router"]          # Tesla: not indexed
    assert not by_id["un_13"]["judged_at_router"] and not by_id["un_01"]["judged_at_router"]      # false premise, odd question
    assert by_id["un_05"]["judged_at_router"]                                                      # personal information
    narrative = next(i for i in items if i["group"] == "narrative")
    assert narrative["tickers"] and narrative["fiscal_year"] and narrative["gold_chunk_ids"]


def test_judging_route_ticker_and_year():
    item = {"id": "x", "group": "narrative", "question": "q", "accept": {"text", "both"}, "tickers": ["NVDA"], "fiscal_year": 2025}
    good = judge(item, Route("q", "text", tickers=["NVDA"], text_years={"NVDA": 2025}))
    assert good["route_ok"] and good["tickers_ok"] and good["year_ok"]
    wrong_year = judge(item, Route("q", "both", tickers=["NVDA"], text_years={"NVDA": 2026}))
    assert wrong_year["route_ok"] and not wrong_year["year_ok"]
    refused = judge(item, Route("q", "text", tickers=["NVDA"], refused=True, refusal="no"))
    assert outcome(Route("q", "sql", refused=True)) == "refuse" and not refused["route_ok"] and "tickers_ok" not in refused


def test_summary_counts_wrong_refusals_and_skips_questions_the_router_cannot_judge(capsys):
    recs = [
        {"id": "a", "group": "numeric", "question": "q", "accept": ["sql"], "got": "sql", "route_ok": True, "tickers": [],
         "fiscal_years": [], "text_years": {}, "refusal": "", "fallback": False, "judged_at_router": True},
        {"id": "b", "group": "narrative", "question": "q", "accept": ["both", "text"], "got": "refuse", "route_ok": False,
         "tickers": [], "fiscal_years": [], "text_years": {}, "refusal": "r", "fallback": False, "judged_at_router": True},
        {"id": "c", "group": "unanswerable", "question": "q", "accept": ["refuse", "text"], "got": "text", "route_ok": True,
         "tickers": [], "fiscal_years": [], "text_years": {}, "refusal": "", "fallback": False, "judged_at_router": False},
    ]
    s = summarize(recs)
    assert s["routing"] == {"numeric": 1.0, "narrative": 0.0, "all": 0.5} and s["wrongly_refused"] == 1 and s["answerable"] == 2
    assert "to review" in capsys.readouterr().out


def test_stopped_by_names_the_layer():
    assert stopped_by({"not_found": False}) == "ANSWERED"
    assert stopped_by({"not_found": True, "trace": ["router: text (refused)", "refuse: not indexed"]}) == "router"
    assert stopped_by({"not_found": True, "trace": ["router: text", "writer: no evidence, not calling the model"]}).startswith("no evidence")
    assert stopped_by({"not_found": True, "trace": ["router: text", "writer: the model found no answer in the evidence"]}) == "writer (NOT_FOUND)"