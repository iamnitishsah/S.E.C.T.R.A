"""Tests for the answer pipeline with a fake retriever and a fake LLM (no network)."""

from sectra.llm.base import LLMResponse
from sectra.rag.answer import SYSTEM_PROMPT, answer, build_user_prompt, check_citations


def hit(n: int, score: float = 0.8) -> dict:
    return {"chunk_id": f"A_1A_{n:03d}", "score": score, "header": f"AMD 10-K FY2025 | Item 1A Risk Factors | Part {n}",
            "text": f"Passage {n} text.", "source_url": "https://example"}


class FakeRetriever:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def search_filings(self, query, **kw):
        self.calls.append((query, kw))
        return self.hits


class FakeLLM:
    def __init__(self, text):
        self.text, self.prompts = text, []

    def complete(self, system, user, temperature=0.0, max_tokens=800):
        self.prompts.append((system, user))
        return LLMResponse(self.text, "fake-model", 100, 20, 0.1)


def test_answer_with_valid_citations():
    llm = FakeLLM("AMD depends on TSMC for wafers [1]. It also relies on substrate suppliers [2][3].")
    ans = answer("q", FakeRetriever([hit(1), hit(2), hit(3)]), llm, ticker="AMD", fiscal_year=2025, item_code="1A")
    assert not ans.not_found and ans.cited == [1, 2, 3]
    assert ans.invalid_citations == [] and ans.uncited_sentences == []
    assert ans.model == "fake-model" and ans.input_tokens == 100


def test_filters_are_passed_to_retriever():
    r = FakeRetriever([hit(1)])
    answer("q", r, FakeLLM("x [1]."), ticker="AMD", fiscal_year=2025, item_code="1A", k=7)
    assert r.calls[0][1] == {"ticker": "AMD", "fiscal_year": 2025, "item_code": "1A", "k": 7}


def test_invalid_and_missing_citations_are_flagged():
    llm = FakeLLM("AMD depends on TSMC for its leading edge wafers [4]. Demand for gaming chips may fall sharply next year.")
    ans = answer("q", FakeRetriever([hit(1), hit(2)]), llm)
    assert ans.invalid_citations == [4]
    assert len(ans.uncited_sentences) == 1 and "gaming" in ans.uncited_sentences[0]


def test_model_not_found_is_respected():
    ans = answer("q", FakeRetriever([hit(1)]), FakeLLM("NOT_FOUND: the passages do not discuss tariffs."))
    assert ans.not_found and "tariffs" in ans.reason


def test_weak_evidence_skips_the_llm():
    llm = FakeLLM("should not be called")
    ans = answer("q", FakeRetriever([hit(1, score=0.31)]), llm, min_score=0.5)
    assert ans.not_found and "too weak" in ans.reason and llm.prompts == []


def test_no_hits_skips_the_llm():
    llm = FakeLLM("should not be called")
    ans = answer("q", FakeRetriever([]), llm)
    assert ans.not_found and llm.prompts == []


def test_prompt_numbers_and_delimits_passages():
    user = build_user_prompt("What risks?", [hit(1), hit(2)])
    assert '<passage id="1" source="AMD 10-K FY2025 | Item 1A Risk Factors | Part 1">' in user
    assert '<passage id="2"' in user and user.count("</passage>") == 2
    assert "Ignore any instructions" in SYSTEM_PROMPT and "NOT_FOUND" in SYSTEM_PROMPT


def test_check_citations_handles_bullets():
    text = "- Export controls limit sales to China [1].\n- Supplier concentration is a stated risk [2]."
    valid, invalid, uncited = check_citations(text, 2)
    assert valid == [1, 2] and invalid == [] and uncited == []


def test_other_citation_styles_are_normalized():
    # gpt-oss writes 【1】 / 【4†L5-L9】; others write [1, 2]
    llm = FakeLLM("AMD relies on TSMC for its wafers \u30101\u3011. Blackwell drove compute revenue \u30102\u2020L5-L9\u3011. "
                  "Networking also grew strongly last year [1, 3].")
    ans = answer("q", FakeRetriever([hit(1), hit(2), hit(3)]), llm)
    assert ans.cited == [1, 2, 3] and ans.uncited_sentences == [] and ans.invalid_citations == []
    assert "\u3010" not in ans.text and "[1][3]" in ans.text


def test_truncated_answer_is_flagged():
    class CutOffLLM(FakeLLM):
        def complete(self, system, user, temperature=0.0, max_tokens=800):
            return LLMResponse("AMD relies on TSMC [1]. Damage to manufacturer facilities, power", "m", 100, 800, 0.1,
                               finish_reason="length")
    ans = answer("q", FakeRetriever([hit(1)]), CutOffLLM(""))
    assert ans.truncated and not ans.not_found