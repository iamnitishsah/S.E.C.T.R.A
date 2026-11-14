"""Tests for the SQL validator: what must pass, and attack queries that must not."""

import pytest

from sectra.analyst.validator import UnsafeSQL, validate

TABLES = ["financial_metrics", "companies", "filings"]


def ok(sql, max_rows=200):
    return validate(sql, TABLES, max_rows)


def test_plain_select_gets_a_limit():
    q = ok("SELECT ticker, value FROM financial_metrics WHERE canonical_metric = 'revenue' AND fiscal_year = 2025")
    assert q.sql.endswith("LIMIT 200") and q.tables == ["financial_metrics"] and q.limit == 200


def test_existing_limit_is_kept_or_lowered():
    assert ok("SELECT ticker FROM companies LIMIT 5").limit == 5
    q = ok("SELECT ticker FROM companies LIMIT 100000", max_rows=50)
    assert q.limit == 50 and q.sql.endswith("LIMIT 50")


def test_joins_ctes_subqueries_and_unions_are_allowed():
    q = ok("""
           WITH growth AS (
               SELECT a.ticker, (a.value - b.value) / b.value AS g
               FROM financial_metrics a JOIN financial_metrics b
                                             ON a.cik = b.cik AND a.canonical_metric = b.canonical_metric AND a.fiscal_year = b.fiscal_year + 1
               WHERE a.canonical_metric = 'revenue' AND a.fiscal_year = 2025
           )
           SELECT g.ticker, c.sector, g.g FROM growth g JOIN companies c ON c.ticker = g.ticker
           WHERE g.g > (SELECT AVG(g) FROM growth) ORDER BY g.g DESC""")
    assert q.tables == ["companies", "financial_metrics"]
    u = ok("SELECT ticker FROM companies WHERE sector = 'energy' UNION SELECT ticker FROM financial_metrics")
    assert u.sql.endswith("LIMIT 200")


def test_comments_do_not_reach_the_database():
    q = ok("SELECT ticker FROM companies /*! UNION SELECT user FROM mysql.user */ -- trailing")
    assert "mysql" not in q.sql and "--" not in q.sql and "/*" not in q.sql


def test_common_functions_pass():
    q = ok("""SELECT ticker, ROUND(SUM(value) / 1e9, 2), COALESCE(MAX(value), 0), IFNULL(MIN(value), 0),
                     CONCAT(ticker, '-', fiscal_year), ABS(AVG(value)), IF(SUM(value) > 0, 'p', 'l'),
                     CASE WHEN COUNT(*) > 1 THEN 1 ELSE 0 END, NULLIF(COUNT(DISTINCT fiscal_year), 0),
                     RANK() OVER (ORDER BY SUM(value) DESC), YEAR(CURDATE()), FORMAT(SUM(value), 0)
              FROM financial_metrics GROUP BY ticker, fiscal_year""")
    assert q.tables == ["financial_metrics"]


@pytest.mark.parametrize("sql", [
    "DELETE FROM financial_metrics",
    "UPDATE companies SET sector = 'x'",
    "INSERT INTO companies (cik) VALUES ('1')",
    "DROP TABLE filings",
    "CREATE TABLE t AS SELECT * FROM companies",
    "TRUNCATE TABLE filings",
    "GRANT ALL ON *.* TO 'x'@'%'",
    "SET GLOBAL max_connections = 1",
    "SHOW TABLES",
    "CALL some_procedure()",
    "SELECT * FROM companies; DROP TABLE companies",
    "SELECT * FROM companies INTO OUTFILE '/tmp/x'",
    "SELECT * FROM companies FOR UPDATE",
    "SELECT * FROM financial_facts",
    "SELECT * FROM mysql.user",
    "SELECT table_name FROM information_schema.tables",
    "SELECT * FROM sectra.companies",
    "SELECT * FROM companies WHERE cik IN (SELECT cik FROM financial_facts)",
    "SELECT SLEEP(10) FROM companies",
    "SELECT BENCHMARK(100000000, MD5('a')) FROM companies",
    "SELECT LOAD_FILE('/etc/passwd') FROM companies",
    "SELECT @@version FROM companies",
    "SELECT VERSION() FROM companies",
    "SELECT DATABASE() FROM companies",
    "SELECT CURRENT_USER() FROM companies",
    "SELECT USER() FROM companies",
    "SELECT CONNECTION_ID() FROM companies",
    "SELECT 1",
    "SELECT @x := 1 FROM companies",
    "SELECT ticker FROM companies LIMIT (SELECT COUNT(*) FROM filings)",
    "this is not sql",
    "",
])
def test_unsafe_queries_are_rejected(sql):
    with pytest.raises(UnsafeSQL):
        validate(sql, TABLES)


def test_error_message_names_the_allowed_tables():
    with pytest.raises(UnsafeSQL, match="companies, filings, financial_metrics"):
        validate("SELECT * FROM financial_facts", TABLES)