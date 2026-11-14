"""Tests for the SQL evaluation scoring (no database, no LLM)."""

from types import SimpleNamespace

from sectra.analyst.tools import QueryResult
from sectra.evaluation.sql_eval import compare, score, values_match


def res(columns, rows):
    return QueryResult(True, "", columns, rows)


GOLD = res(["ticker", "fiscal_year", "revenue_bn"], [["NVDA", 2025, 130.5], ["AMD", 2025, 34.64]])


def test_same_result_in_a_different_shape_passes():
    pred = res(["fiscal_year", "ticker", "source_accession", "rev"], [[2025, "AMD", "acc", 34.64], [2025, "NVDA", "acc", 130.5]])
    assert compare(GOLD, pred) == (True, "")


def test_raw_dollars_and_fractions_match_scaled_gold_values():
    assert compare(GOLD, res(["ticker", "fiscal_year", "value"], [["NVDA", 2025, 130497000000], ["AMD", 2025, 34640000000]]))[0]
    gold = res(["ticker", "fiscal_year", "margin_pct"], [["AAPL", 2025, 46.91]])
    assert compare(gold, res(["ticker", "fiscal_year", "margin"], [["AAPL", 2025, 0.4691]]))[0]
    assert values_match(72.88, 72.884) and not values_match(72.88, 73.5) and not values_match(46.91, 46.21)


def test_wrong_value_missing_row_and_extra_row_fail():
    assert "expected 34.64" in compare(GOLD, res(["ticker", "fiscal_year", "x"], [["NVDA", 2025, 130.5], ["AMD", 2025, 22.7]]))[1]
    assert "missing" in compare(GOLD, res(["ticker", "fiscal_year", "x"], [["NVDA", 2025, 130.5]]))[1]
    extra = res(["ticker", "fiscal_year", "x"], [["NVDA", 2025, 130.5], ["AMD", 2025, 34.64], ["INTC", 2025, 52.85]])
    assert "extra" in compare(GOLD, extra)[1]
    assert "no ticker" in compare(GOLD, res(["name", "x"], [["NVIDIA", 130.5]]))[1]


def test_wrong_year_fails_when_the_year_is_returned():
    assert not compare(GOLD, res(["ticker", "fiscal_year", "x"], [["NVDA", 2024, 130.5], ["AMD", 2024, 34.64]]))[0]


def test_aggregates_without_a_ticker():
    gold = res(["sector", "fiscal_year", "total_bn"], [["energy", 2025, 512.3]])
    assert compare(gold, res(["total_revenue_bn"], [[512.3]]))[0]              # no key columns shared: values only
    assert compare(gold, res(["sector", "total"], [["energy", 512300000000]]))[0]
    assert not compare(gold, res(["total"], [[512.3], [99.0]]))[0]             # an extra row
    count = res(["fiscal_year", "n_companies"], [[2025, 7]])
    assert compare(count, res(["n"], [[7]]))[0] and not compare(count, res(["n"], [[20]]))[0]


def test_scoring_of_no_data_questions():
    q = {"expect": "no_data"}
    assert score(q, SimpleNamespace(rows=[], cannot_answer=True, reason="x"), None)[0]
    assert score(q, SimpleNamespace(rows=[], cannot_answer=False, reason=""), None)[0]
    assert not score(q, SimpleNamespace(rows=[["PFE", 2025, 1.0]], cannot_answer=False, reason=""), None)[0]
    declined = SimpleNamespace(rows=[], cannot_answer=True, reason="no such metric", sql="", columns=[])
    assert score({"expect": "rows"}, declined, GOLD) == (False, "declined: no such metric")