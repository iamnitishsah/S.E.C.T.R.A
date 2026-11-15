"""Tests for the HTTP API with the same fakes as the graph tests (no services, no network)."""

import pytest
from fastapi.testclient import TestClient

from sectra.api.main import RateLimiter, create_app
from tests.test_graph import GROWTH_SQL, ScriptedLLM, deps, route_json  # noqa: F401  (deps is a fixture)


@pytest.fixture()
def client(deps, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.delenv("SECTRA_API_KEY", raising=False)
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "0")
    monkeypatch.setattr("sectra.agents.graph.ROOT", tmp_path)             # the run log goes to a temp folder
    deps.llm = ScriptedLLM()
    with TestClient(create_app(deps)) as c:
        c.deps = deps
        yield c


def test_health_and_companies(client):
    assert client.get("/health").json()["companies"] == 2
    rows = client.get("/companies").json()
    assert [r["ticker"] for r in rows] == ["AMD", "NVDA"]
    assert rows[1]["text_years"] == [2024, 2025, 2026] and rows[1]["metric_years"] == [2009, 2026]


def test_hybrid_question_returns_table_passages_and_steps(client, tmp_path):
    client.deps.llm.replies = [
        route_json(route="both", companies=["Nvidia"], fiscal_years=[2025], sql_question="growth?", text_question="why?"),
        GROWTH_SQL, "NVIDIA's revenue grew 114.2% in fiscal 2025 [T]. Data Center demand drove the growth [1]."]
    r = client.post("/ask", json={"question": "How fast did Nvidia grow in fiscal 2025 and why?"})
    body = r.json()
    assert r.status_code == 200 and body["answered"] and body["route"] == "both" and body["tickers"] == ["NVDA"]
    assert body["table"]["rows"] == [["NVDA", 2025, 114.2, "acc-1"]] and body["table"]["source_filings"] == ["acc-1"]
    assert len(body["passages"]) == 5 and body["passages"][0]["cited"] and not body["passages"][1]["cited"]
    assert body["warnings"] == {} and [s.split(":")[0] for s in body["steps"]] == ["router", "sql", "text", "writer"]
    assert body["input_tokens"] == 300 and (tmp_path / "data/logs/graph.jsonl").exists()


def test_refused_question_is_a_normal_response_not_an_error(client):
    client.deps.llm.replies = [route_json(route="text", companies=["Tesla"])]
    body = client.post("/ask", json={"question": "What risks did Tesla describe?"}).json()
    assert not body["answered"] and "Tesla" in body["reason"] and body["table"] is None and body["passages"] == []


def test_bad_input_and_upstream_failure(client):
    assert client.post("/ask", json={"question": "hi"}).status_code == 422
    assert client.post("/ask", json={}).status_code == 422
    client.deps.llm.replies = []                                          # the fake LLM runs out: an upstream failure
    r = client.post("/ask", json={"question": "What drove Nvidia's growth?"})
    assert r.status_code == 502 and "could not be processed" in r.json()["detail"]


def test_api_key_is_required_when_configured(client, monkeypatch):
    monkeypatch.setenv("SECTRA_API_KEY", "secret")
    assert client.post("/ask", json={"question": "What risks did Tesla describe?"}).status_code == 401
    client.deps.llm.replies = [route_json(route="text", companies=["Tesla"])]
    ok = client.post("/ask", json={"question": "What risks did Tesla describe?"}, headers={"X-API-Key": "secret"})
    assert ok.status_code == 200 and client.get("/health").status_code == 200       # health needs no key


def test_rate_limiter_window():
    lim = RateLimiter(2)
    assert lim.allow("a", 0) and lim.allow("a", 1) and not lim.allow("a", 2)
    assert lim.allow("b", 2)                                              # another client is unaffected
    assert lim.allow("a", 61)                                             # the first call has left the window
    assert RateLimiter(0).allow("a", 0)