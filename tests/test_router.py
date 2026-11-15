"""Tests for the router: name resolution, reply parsing, routing with a scripted LLM, corpus checks."""

import json

from sectra.agents.router import Catalog, check_corpus, normalize_name, parse_reply, resolve_company, route
from sectra.llm.base import LLMResponse

CATALOG = Catalog(
    companies={"NVDA": {"name": "NVIDIA CORP", "sector": "semiconductors"},
               "AMZN": {"name": "AMAZON COM INC", "sector": "technology"},
               "LLY": {"name": "ELI LILLY & Co", "sector": "healthcare"},
               "JNJ": {"name": "JOHNSON & JOHNSON", "sector": "healthcare"},
               "MPC": {"name": "Marathon Petroleum Corp", "sector": "energy"},
               "GOOGL": {"name": "Alphabet Inc.", "sector": "technology"},
               "INTC": {"name": "INTEL CORP", "sector": "semiconductors"}},
    text_years={"NVDA": [2023, 2024, 2025, 2026], "AMZN": [2022, 2023, 2024, 2025], "LLY": [2022, 2023, 2024, 2025]},
    metric_years={t: (2009, 2026) for t in ("NVDA", "AMZN", "LLY", "JNJ", "MPC", "GOOGL", "INTC")},
    metrics=["net_income", "revenue"],
    aliases={"google": "GOOGL", "lilly": "LLY", "j&j": "JNJ"})


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user, temperature=0.0, max_tokens=800):
        self.calls.append((system, user))
        return LLMResponse(self.replies.pop(0), "fake", 50, 10, 0.2)


def reply(**kw):
    base = {"route": "text", "companies": [], "fiscal_years": [], "sql_question": "", "text_question": "", "reason": "r"}
    return json.dumps({**base, **kw})


def decide(question, *replies):
    return check_corpus(route(question, ScriptedLLM(*replies), CATALOG), CATALOG)


def test_company_names_resolve_to_tickers():
    assert normalize_name("AMAZON COM INC") == "amazon" and normalize_name("ELI LILLY & Co") == "eli lilly"
    for mention, ticker in [("nvda", "NVDA"), ("Nvidia", "NVDA"), ("NVIDIA Corporation", "NVDA"), ("Amazon", "AMZN"),
                            ("Eli Lilly", "LLY"), ("Lilly", "LLY"), ("Johnson & Johnson", "JNJ"), ("J&J", "JNJ"),
                            ("Google", "GOOGL"), ("Alphabet", "GOOGL"), ("Marathon Petroleum", "MPC")]:
        assert resolve_company(mention, CATALOG) == ticker, mention
    for mention in ("Tesla", "Marathon Oil", "Walmart", "", "Corp"):
        assert resolve_company(mention, CATALOG) is None, mention


def test_reply_parsing_tolerates_wrapping_and_rejects_bad_routes():
    assert parse_reply('Here you go:\n```json\n{"route": "sql"}\n```')["route"] == "sql"
    assert parse_reply("no json here") is None and parse_reply('{"route": "maybe"}') is None
    assert parse_reply("{not json}") is None


def test_sql_and_text_routes_fill_their_question():
    r = decide("What was Nvidia's revenue in fiscal 2025?", reply(route="sql", companies=["Nvidia"], fiscal_years=[2025]))
    assert (r.route, r.tickers, r.fiscal_years, r.refused) == ("sql", ["NVDA"], [2025], False)
    assert r.sql_question == "What was Nvidia's revenue in fiscal 2025?" and r.text_question == ""
    r = decide("What risks does Amazon describe?", reply(route="text", companies=["Amazon"]))
    assert r.route == "text" and r.text_years == {"AMZN": 2025}             # no year named -> latest indexed filing
    assert r.text_question == "What risks does Amazon describe?"


def test_both_route_keeps_two_sub_questions_and_the_named_year():
    r = decide("q", reply(route="both", companies=["NVDA"], fiscal_years=["2025"], sql_question="revenue growth?",
                          text_question="what drove growth?"))
    assert (r.route, r.sql_question, r.text_question, r.text_years) == ("both", "revenue growth?", "what drove growth?", {"NVDA": 2025})


def test_unknown_company_is_refused_before_any_search():
    r = decide("What supply chain risks did Tesla describe?", reply(route="text", companies=["Tesla"]))
    assert r.refused and "Tesla" in r.refusal and "indexed:" in r.refusal


def test_year_without_a_filing_is_refused_for_text():
    r = decide("q", reply(route="text", companies=["NVDA"], fiscal_years=[2012]))
    assert r.refused and "fiscal 2012" in r.refusal and "2023, 2024, 2025, 2026" in r.refusal
    r = decide("q", reply(route="sql", companies=["NVDA"], fiscal_years=[2030]))
    assert r.refused and "2009-2026" in r.refusal
    r = decide("q", reply(route="sql", companies=["NVDA"], fiscal_years=[2012]))     # metrics go back further than text
    assert not r.refused


def test_both_is_reduced_when_one_side_is_missing():
    r = decide("q", reply(route="both", companies=["Intel"], fiscal_years=[2025]))
    assert r.route == "sql" and not r.refused and "no filing text is indexed for INTC" in r.notes[0]
    r = decide("q", reply(route="both", companies=["NVDA"], fiscal_years=[2030]))
    assert r.refused                                                         # neither side has fiscal 2030


def test_none_route_is_refused_with_the_routers_reason():
    r = decide("Should I buy NVIDIA stock?", reply(route="none", companies=["NVIDIA"], reason="investment advice"))
    assert r.refused and r.refusal == "investment advice"


def test_unparseable_reply_is_retried_then_falls_back_to_text():
    llm = ScriptedLLM("I think this is about numbers", reply(route="sql", companies=["NVDA"]))
    r = route("q", llm, CATALOG)
    assert r.route == "sql" and len(llm.calls) == 2 and "JSON object only" in llm.calls[1][1] and r.input_tokens == 100
    r = route("q", ScriptedLLM("nope", "still nope"), CATALOG)
    assert r.route == "text" and r.fallback and r.text_question == "q"


def test_metric_names_are_in_the_prompt():
    llm = ScriptedLLM(reply())
    route("q", llm, CATALOG)
    assert "net_income, revenue" in llm.calls[0][0]