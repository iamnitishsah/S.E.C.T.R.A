"""Tests for reranked retrieval with a fake dense retriever and a fake reranker (no network)."""

from sectra.retrieval.reranker import RerankRetriever


def hit(cid, score):
    return {"chunk_id": cid, "score": score, "header": "h", "text": cid}


class FakeDense:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def search_filings(self, query, **kw):
        self.calls.append(kw)
        return self.hits[: kw["k"]]


class FakeReranker:
    def __init__(self, scores):
        self.scores = scores

    def score(self, query, hits):
        return [self.scores[h["chunk_id"]] for h in hits]


def test_pool_comes_from_dense_and_is_resorted():
    dense = FakeDense([hit("a", 0.9), hit("b", 0.8), hit("c", 0.7), hit("d", 0.6)])
    r = RerankRetriever(dense, FakeReranker({"a": 0.1, "b": 0.5, "c": 0.9}), candidates=3, default_k=2)
    out = r.search_filings("q", ticker="AMD", fiscal_year=2025)
    assert dense.calls == [{"ticker": "AMD", "fiscal_year": 2025, "item_code": None, "k": 3}]
    assert r.last_pool == ["a", "b", "c"]                       # "d" was outside the candidate pool
    assert [h["chunk_id"] for h in out] == ["c", "b"]           # re-sorted by rerank score, cut to k
    assert out[0]["score"] == 0.9 and out[0]["dense_score"] == 0.7


def test_explicit_k_overrides_default():
    dense = FakeDense([hit("a", 0.9), hit("b", 0.8), hit("c", 0.7)])
    r = RerankRetriever(dense, FakeReranker({"a": 0.3, "b": 0.2, "c": 0.1}), candidates=3, default_k=1)
    assert [h["chunk_id"] for h in r.search_filings("q", k=3)] == ["a", "b", "c"]
