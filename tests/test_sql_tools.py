"""Tests for the SQL Analyst tools against an in-memory SQLite database (no MySQL needed)."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from sectra.analyst.tools import _plain, format_rows, get_schema, run_readonly_sql

CFG = {"allowed_tables": ["financial_metrics", "companies", "filings"], "max_rows": 3, "timeout_ms": 5000}


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE companies (cik TEXT, ticker TEXT, name TEXT, sector TEXT)"))
        conn.execute(text("CREATE TABLE financial_metrics (cik TEXT, ticker TEXT, sector TEXT, fiscal_year INT, "
                          "canonical_metric TEXT, value NUMERIC, unit TEXT, source_accession TEXT)"))
        conn.execute(text("CREATE TABLE financial_facts (cik TEXT)"))
        for cik, ticker, sector in (("1", "AMD", "semiconductors"), ("2", "NVDA", "semiconductors"), ("3", "CVX", "energy")):
            conn.execute(text("INSERT INTO companies VALUES (:c, :t, :t, :s)"), {"c": cik, "t": ticker, "s": sector})
            for fy in (2024, 2025):
                conn.execute(text("INSERT INTO financial_metrics VALUES (:c, :t, :s, :fy, 'revenue', :v, 'USD', 'acc')"),
                             {"c": cik, "t": ticker, "s": sector, "fy": fy, "v": int(cik) * 1000 + fy})
        conn.execute(text("INSERT INTO financial_metrics VALUES ('1', 'AMD', 'semiconductors', 2025, 'gross_profit', 5, 'USD', 'acc')"))
    return eng


def test_query_runs_and_reports_the_executed_sql(engine):
    r = run_readonly_sql("SELECT ticker, value FROM financial_metrics WHERE fiscal_year = 2025 "
                         "AND canonical_metric = 'revenue' ORDER BY value DESC LIMIT 2", engine, CFG)
    assert r.ok and r.columns == ["ticker", "value"]
    assert r.rows == [["CVX", 5025], ["NVDA", 4025]] and r.sql.endswith("LIMIT 2")
    assert not r.truncated


def test_limit_is_enforced_and_truncation_is_flagged(engine):
    r = run_readonly_sql("SELECT ticker FROM financial_metrics", engine, CFG)
    assert r.ok and len(r.rows) == 3 and r.truncated
    assert not run_readonly_sql("SELECT ticker FROM companies WHERE sector = 'energy'", engine, CFG).truncated


def test_unsafe_query_is_rejected_without_touching_the_database(engine):
    r = run_readonly_sql("DELETE FROM companies", engine, CFG)
    assert not r.ok and r.error.startswith("rejected:") and r.sql == ""
    r = run_readonly_sql("SELECT * FROM financial_facts", engine, CFG)
    assert not r.ok and "not available" in r.error
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM companies")).scalar() == 3


def test_database_errors_come_back_as_text(engine):
    r = run_readonly_sql("SELECT no_such_column FROM companies", engine, CFG)
    assert not r.ok and r.error.startswith("database error:") and "no_such_column" in r.error


def test_colons_in_string_literals_are_not_treated_as_parameters(engine):
    r = run_readonly_sql("SELECT ticker FROM companies WHERE name = 'a:b'", engine, CFG)
    assert r.ok and r.rows == []


def test_schema_lists_sectors_years_and_metric_coverage(engine):
    s = get_schema(engine)
    assert "semiconductors: AMD (AMD), NVDA (NVDA)" in s and "energy: CVX (CVX)" in s
    assert "2024 to 2025" in s
    assert "revenue (USD; 3)" in s and "gross_profit (USD; 1)" in s
    assert "2024 to 2025" in s and "names none: 2025" in s


def test_plain_values_and_formatting():
    assert _plain(Decimal("391035000000.000000")) == 391035000000 and isinstance(_plain(Decimal("5.0")), int)
    assert _plain(Decimal("6.11")) == 6.11
    r = run_readonly_sql("DROP TABLE companies", None, CFG)
    assert format_rows(r).startswith("rejected:")