"""Tests for the SQL Analyst loop with a scripted fake LLM and an in-memory SQLite database."""

import pytest
from sqlalchemy import create_engine, text

from sectra.analyst.agent import ask_sql, extract_sql, unsupported_numbers
from sectra.analyst.tools import QueryResult
from sectra.llm.base import LLMResponse

CFG = {"allowed_tables": ["financial_metrics", "companies", "filings"], "max_rows": 50, "timeout_ms": 5000}
GOOD = ("```sql\nSELECT ticker, fiscal_year, ROUND(value / 1e9, 2) AS revenue_bn, source_accession "
        "FROM financial_metrics WHERE canonical_metric = 'revenue' ORDER BY value DESC\n```")


class ScriptedLLM:
    """Returns the given replies in order and records every prompt."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user, temperature=0.0, max_tokens=800):
        self.calls.append((system, user))
        return LLMResponse(self.replies.pop(0), "fake-model", 100, 20, 0.5)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE companies (cik TEXT, ticker TEXT, name TEXT, sector TEXT)"))
        conn.execute(text("CREATE TABLE financial_metrics (cik TEXT, ticker TEXT, sector TEXT, fiscal_year INT, "
                          "canonical_metric TEXT, value NUMERIC, unit TEXT, source_accession TEXT)"))
        for cik, ticker, value in (("1", "NVDA", 130497000000), ("2", "AMD", 34640000000)):
            conn.execute(text("INSERT INTO companies VALUES (:c, :t, :t, 'semiconductors')"), {"c": cik, "t": ticker})
            conn.execute(text("INSERT INTO financial_metrics VALUES (:c, :t, 'semiconductors', 2025, 'revenue', :v, "
                              "'USD', :a)"), {"c": cik, "t": ticker, "v": value, "a": f"acc-{ticker}"})
    return eng


def test_question_to_sql_to_answer(engine):
    llm = ScriptedLLM(GOOD, "NVIDIA had the highest revenue in fiscal 2025 at 130.5 billion; AMD had 34.64 billion.")
    ans = ask_sql("Which company had the highest revenue in fiscal 2025?", llm, engine, CFG, schema="SCHEMA")
    assert not ans.cannot_answer and ans.rows[0][:3] == ["NVDA", 2025, 130.5]
    assert ans.sql.endswith("LIMIT 50") and ans.sources == ["acc-AMD", "acc-NVDA"]
    assert ans.unsupported_numbers == [] and len(ans.attempts) == 1
    assert "SCHEMA" in llm.calls[0][0]                              # the schema is in the SQL prompt
    assert "130.5" in llm.calls[1][1] and "LIMIT 50" in llm.calls[1][1]   # the answer call sees the rows and the SQL
    assert ans.input_tokens == 200 and ans.latency_s == 1.0        # both calls are counted


def test_failed_query_is_retried_with_the_error(engine):
    llm = ScriptedLLM("```sql\nSELECT revenue FROM financial_metrics\n```", GOOD, "NVIDIA: 130.5 billion.")
    ans = ask_sql("revenue?", llm, engine, CFG, schema="S")
    assert len(ans.attempts) == 2 and ans.attempts[0]["error"].startswith("database error")
    assert "It failed: database error" in llm.calls[1][1] and "SELECT revenue FROM" in llm.calls[1][1]
    assert ans.rows and not ans.cannot_answer


def test_unsafe_query_is_rejected_then_gives_up_after_max_attempts(engine):
    llm = ScriptedLLM("```sql\nDELETE FROM companies\n```", "```sql\nSELECT * FROM financial_facts\n```")
    ans = ask_sql("delete everything", llm, engine, CFG, schema="S", max_attempts=2)
    assert ans.cannot_answer and "2 attempts" in ans.reason and ans.rows == []
    assert all(a["error"].startswith("rejected") for a in ans.attempts)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM companies")).scalar() == 2


def test_model_can_decline(engine):
    llm = ScriptedLLM("CANNOT_ANSWER: stock prices are not in the database.")
    ans = ask_sql("What is NVIDIA's share price?", llm, engine, CFG, schema="S")
    assert ans.cannot_answer and "stock prices" in ans.reason and len(llm.calls) == 1 and ans.sql == ""


def test_empty_result_still_gets_an_answer(engine):
    llm = ScriptedLLM("```sql\nSELECT ticker, fiscal_year, value FROM financial_metrics "
                      "WHERE canonical_metric = 'gross_profit'\n```", "The database has no gross profit for these companies.")
    ans = ask_sql("gross profit?", llm, engine, CFG, schema="S")
    assert not ans.cannot_answer and ans.rows == [] and "(no rows)" in llm.calls[1][1]


def test_numbers_not_in_the_rows_are_flagged(engine):
    llm = ScriptedLLM(GOOD, "NVIDIA earned 130.5 billion in fiscal 2025, about 3.8 times AMD's 34.6 billion, up 114%.")
    ans = ask_sql("Compare revenue in fiscal 2025", llm, engine, CFG, schema="S")
    assert ans.unsupported_numbers == ["3.8", "114"]


def test_number_matching_rules():
    r = QueryResult(True, "", ["ticker", "fy", "x", "acc"], [["AVGO", 2025, 63.89, "0001730168-25-000121"]])
    assert unsupported_numbers("AVGO reported 63.89 in 2025 (63.9 rounded).", r, "q") == []
    assert unsupported_numbers("AVGO reported 64 in 2025.", r, "q") == []           # 63.89 rounds to 64
    assert unsupported_numbers("AVGO reported 63.8.", r, "q") == ["63.8"]
    assert unsupported_numbers("The top 3 were ...", r, "Show the top 3") == []       # number from the question
    assert unsupported_numbers("Filing 0001730168-25-000121.", r, "q") == []          # digits inside an accession
    assert unsupported_numbers("Per its 10-K for FY2025, AVGO reported 63.89.", r, "q") == []
    fell = QueryResult(True, "", ["ticker", "fy", "growth_pct"], [["AMD", 2023, -3.9]])
    assert unsupported_numbers("AMD's revenue fell by 3.9% in 2023.", fell, "q") == []


def test_extract_sql():
    assert extract_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert extract_sql("Here you go:\n```\nSELECT a FROM t\n```\nDone.") == "SELECT a FROM t"
    assert extract_sql("SELECT a FROM t;") == "SELECT a FROM t"