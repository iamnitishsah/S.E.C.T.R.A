"""Tests for the research graph with a scripted LLM, a fake retriever and SQLite (no services)."""

import json

import pytest
from sqlalchemy import create_engine, text

from sectra.agents.graph import build_graph
from sectra.agents.nodes import Deps, text_targets
from sectra.agents.router import Catalog, Route
from sectra.analyst.agent import SQLAnswer
from sectra.llm.base import LLMResponse
from sqlalchemy.pool import StaticPool

SQL_CFG = {"allowed_tables": ["financial_metrics", "companies", "filings"], "max_rows": 50, "timeout_ms": 5000}
GROWTH_SQL = ("```sql\nSELECT ticker, fiscal_year, value AS growth_pct, source_accession FROM financial_metrics "
              "WHERE canonical_metric = 'growth' ORDER BY value DESC LIMIT 1\n```")


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user, temperature=0.0, max_tokens=800):
        self.calls.append((system, user))
        return LLMResponse(self.replies.pop(0), "fake-model", 100, 20, 0.5)


class FakeRetriever:
    def __init__(self, score=0.2):
        self.calls, self.score = [], score

    def search_filings(self, query, ticker=None, fiscal_year=None, item_code=None, k=None):
        self.calls.append({"query": query, "ticker": ticker, "fiscal_year": fiscal_year, "k": k})
        return [{"chunk_id": f"{ticker}_{fiscal_year}_{i}", "score": self.score, "url": "u",
                 "header": f"{ticker} 10-K FY{fiscal_year} | Item 7", "text": f"Data Center demand drove growth {i}."}
                for i in range(k)]


def route_json(**kw):
    base = {"route": "text", "companies": [], "fiscal_years": [], "sql_question": "", "text_question": "", "reason": "r"}
    return json.dumps({**base, **kw})


@pytest.fixture()
def deps():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE financial_metrics (cik TEXT, ticker TEXT, sector TEXT, fiscal_year INT, "
                          "canonical_metric TEXT, value NUMERIC, unit TEXT, source_accession TEXT)"))
        conn.execute(text("INSERT INTO financial_metrics VALUES ('1', 'NVDA', 's', 2025, 'growth', 114.2, 'pct', 'acc-1')"))
    catalog = Catalog({"NVDA": {"name": "NVIDIA CORP", "sector": "s"}, "AMD": {"name": "ADVANCED MICRO DEVICES INC", "sector": "s"}},
                      {"NVDA": [2024, 2025, 2026], "AMD": [2024, 2025]}, {"NVDA": (2009, 2026), "AMD": (2009, 2025)}, ["revenue"])
    return Deps(llm=None, retriever=FakeRetriever(), engine=eng, catalog=catalog, sql_cfg=SQL_CFG, schema="SCHEMA",
                top_k=5, min_score=0.05)


def run(deps, question, *replies):
    deps.llm = ScriptedLLM(*replies)
    return build_graph(deps).invoke({"question": question})


def test_text_route_searches_the_named_company_and_cites_passages(deps):
    s = run(deps, "What drove Nvidia's growth?", route_json(route="text", companies=["Nvidia"]),
            "Data Center demand drove the growth in fiscal 2026 [1][2].")
    assert deps.retriever.calls == [{"query": "What drove Nvidia's growth?", "ticker": "NVDA", "fiscal_year": 2026, "k": 5}]
    assert s["checks"]["cited_passages"] == [1, 2] and not s["checks"]["cites_table"] and "sql" not in s
    assert s["trace"][0].startswith("router: text") and s["trace"][1].startswith("text: 5 passages")
    assert s["usage"]["input_tokens"] == 200 and len(deps.llm.calls) == 2


def test_sql_route_skips_retrieval_and_cites_the_table(deps):
    s = run(deps, "How fast did Nvidia grow in fiscal 2025?", route_json(route="sql", companies=["NVDA"], fiscal_years=[2025]),
            GROWTH_SQL, "NVIDIA's revenue grew 114.2% in fiscal 2025 [T].")
    assert deps.retriever.calls == [] and s["sql"].rows == [["NVDA", 2025, 114.2, "acc-1"]]
    assert s["checks"]["cites_table"] and s["checks"]["unsupported_numbers"] == [] and s["checks"]["uncited_sentences"] == []
    assert "RESULT TABLE [T]" in deps.llm.calls[2][1] and "PASSAGES" not in deps.llm.calls[2][1]


def test_both_route_runs_sql_then_text_then_one_writer(deps):
    s = run(deps, "How fast did Nvidia grow in fiscal 2025 and why?",
            route_json(route="both", companies=["Nvidia"], fiscal_years=[2025], sql_question="growth?", text_question="why?"),
            GROWTH_SQL, "NVIDIA's revenue grew 114.2% in fiscal 2025 [T]. Data Center demand drove the growth [1].")
    assert [t.split(":")[0] for t in s["trace"]] == ["router", "sql", "text", "writer"]
    assert deps.retriever.calls[0] == {"query": "why?", "ticker": "NVDA", "fiscal_year": 2025, "k": 5}
    user = deps.llm.calls[2][1]
    assert "RESULT TABLE [T]" in user and '<passage id="1"' in user and "114.2" in user
    assert s["checks"]["cites_table"] and s["checks"]["cited_passages"] == [1]


def test_companies_for_the_text_search_come_from_the_sql_rows_when_the_question_names_none(deps):
    s = run(deps, "Which company grew fastest in fiscal 2025 and what drove it?",
            route_json(route="both", fiscal_years=[2025], sql_question="fastest growth?", text_question="what drove it?"),
            GROWTH_SQL, "NVIDIA grew fastest, at 114.2% [T]. Data Center demand drove it [1].")
    assert deps.retriever.calls[0]["ticker"] == "NVDA" and deps.retriever.calls[0]["fiscal_year"] == 2025
    assert not s["not_found"]


def test_several_companies_get_one_search_each(deps):
    state = {"route": Route("q", "text", tickers=["NVDA", "AMD"], text_years={"NVDA": 2026, "AMD": 2025}, text_question="q")}
    assert text_targets(state, deps) == [("NVDA", 2026), ("AMD", 2025)]
    s = run(deps, "Compare the risks of Nvidia and AMD", route_json(route="text", companies=["Nvidia", "AMD"]), "Both [1][3].")
    assert [(c["ticker"], c["k"]) for c in deps.retriever.calls] == [("NVDA", 2), ("AMD", 2)] and len(s["passages"]) == 4


def test_refused_question_never_reaches_sql_retrieval_or_the_writer(deps):
    s = run(deps, "What risks did Tesla describe?", route_json(route="text", companies=["Tesla"]))
    assert s["not_found"] and "Tesla" in s["reason"] and len(deps.llm.calls) == 1 and deps.retriever.calls == []
    assert [t.split(":")[0] for t in s["trace"]] == ["router", "refuse"]


def test_weak_passages_are_dropped_and_no_evidence_means_no_writer_call(deps):
    deps.retriever = FakeRetriever(score=0.01)
    s = run(deps, "What is Nvidia's favourite colour?", route_json(route="text", companies=["Nvidia"]))
    assert s["not_found"] and len(deps.llm.calls) == 1 and "below min_score" in s["trace"][1]


def test_writer_refusal_and_number_check(deps):
    s = run(deps, "q", route_json(route="text", companies=["NVDA"]), "NOT_FOUND: the passages do not say.")
    assert s["not_found"] and s["reason"] == "the passages do not say."
    s = run(deps, "How fast did Nvidia grow in fiscal 2025?", route_json(route="sql", companies=["NVDA"], fiscal_years=[2025]),
            GROWTH_SQL, "NVIDIA grew 114.2% [T], roughly 3 times faster than peers [T].")
    assert s["checks"]["unsupported_numbers"] == ["3"]


def test_citation_numbers_are_not_checked_as_figures(deps):
    s = run(deps, "What drove Nvidia's growth?", route_json(route="text", companies=["Nvidia"]),
            "- Demand grew. Data Center demand drove the growth in fiscal 2026 [3][4].")
    assert s["checks"]["unsupported_numbers"] == [] and s["checks"]["uncited_sentences"] == []


def test_sql_side_declining_is_told_to_the_writer_in_a_hybrid_question(deps):
    s = run(deps, "q", route_json(route="both", companies=["NVDA"], fiscal_years=[2025], sql_question="iPhone revenue?",
                                  text_question="what drove growth?"),
            "CANNOT_ANSWER: no such metric.", "The database has no such figure. Data Center demand drove growth [1].")
    assert isinstance(s["sql"], SQLAnswer) and s["sql"].cannot_answer
    assert "RESULT TABLE: none" in deps.llm.calls[2][1] and not s["not_found"]


def test_fullwidth_table_citation_is_recognised(deps):
    s = run(deps, "How fast did Nvidia grow in fiscal 2025?", route_json(route="sql", companies=["NVDA"], fiscal_years=[2025]),
            GROWTH_SQL, "NVIDIA's revenue grew 114.2% in fiscal 2025\u3010T\u3011.")
    assert s["checks"]["cites_table"] and s["checks"]["uncited_sentences"] == [] and "[T]" in s["answer"]