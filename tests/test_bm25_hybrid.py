"""Tests for BM25 keyword search and rank fusion."""

import math

from sectra.retrieval.bm25 import BM25Index, tokenize
from sectra.retrieval.hybrid import HybridRetriever, rrf_fuse


def chunk(cid, text, ticker="AMD", year=2025, item="1A"):
    return {"chunk_id": cid, "ticker": ticker, "fiscal_year": year, "item_code": item,
            "header": f"{ticker} 10-K FY{year} | Item {item}", "text": text}


CHUNKS = [
    chunk("a", "We rely on TSMC to manufacture our wafers. Supply risks are significant."),
    chunk("b", "Export controls restrict sales of our products to China."),
    chunk("c", "Revenue increased 30,390 million due to data center demand.", item="7"),
    chunk("d", "We rely on TSMC to manufacture our wafers. Supply risks are significant.", year=2024),
    chunk("e", "Winrevair met the primary endpoint of its trial.", ticker="MRK", item="1"),
]


def test_tokenize():
    assert tokenize("FY2025 10-K: Risks & obligations, $30,390 million (4.5%)") == \
        ["fy", "2025", "10", "k", "risk", "obligation", "30390", "million", "4.5"]
    assert tokenize("business class") == ["business", "class"]        # 'ss' endings kept


def test_rare_term_wins_and_no_match_is_empty():
    idx = BM25Index(CHUNKS)
    assert idx.search_filings("What did the Winrevair trial show?", k=3)[0]["chunk_id"] == "e"
    assert idx.search_filings("zzzz qqqq") == []


def test_year_in_question_picks_the_right_filing():
    idx = BM25Index(CHUNKS)                       # a and d have identical text; only the header year differs
    assert idx.search_filings("In fiscal 2024, who makes wafers?", k=1)[0]["chunk_id"] == "d"
    assert idx.search_filings("In fiscal 2025, who makes wafers?", k=1)[0]["chunk_id"] == "a"


def test_company_name_is_searchable():
    idx = BM25Index(CHUNKS, names={"MRK": "Merck & Co., Inc."})
    assert idx.search_filings("Merck", k=1)[0]["chunk_id"] == "e"


def test_filters_match_dense_behaviour():
    idx = BM25Index(CHUNKS)
    hits = idx.search_filings("TSMC wafers supply", ticker="amd", fiscal_year="2024", k=5)
    assert [h["chunk_id"] for h in hits] == ["d"]
    assert idx.search_filings("revenue data center", item_code=["7"], k=5)[0]["chunk_id"] == "c"
    assert idx.search_filings("TSMC", ticker="MRK") == []


def test_score_formula_for_one_term():
    idx = BM25Index(CHUNKS, k1=1.2, b=0.75)
    n, df, tf = len(CHUNKS), 1, 1                                    # 'winrevair' is in one chunk, once
    lengths = [len(tokenize(f"{c['ticker']}  {c['header']}\n{c['text']}")) for c in CHUNKS]
    norm = 1.2 * (1 - 0.75 + 0.75 * lengths[4] / (sum(lengths) / n))
    expected = math.log(1 + (n - df + 0.5) / (df + 0.5)) * tf * 2.2 / (tf + norm)
    assert abs(idx.search_filings("winrevair", k=1)[0]["score"] - expected) < 1e-4


def test_rrf_prefers_chunks_found_by_both():
    dense = [{"chunk_id": "x", "score": 0.9}, {"chunk_id": "y", "score": 0.8}, {"chunk_id": "z", "score": 0.7}]
    bm25 = [{"chunk_id": "y", "score": 12.0}, {"chunk_id": "w", "score": 9.0}]
    fused = rrf_fuse({"dense": dense, "bm25": bm25}, rrf_k=60)
    assert [h["chunk_id"] for h in fused] == ["y", "x", "w", "z"]
    assert abs(fused[0]["score"] - (1 / 62 + 1 / 61)) < 1e-9
    assert fused[0]["ranks"] == {"dense": 2, "bm25": 1} and fused[0]["dense_score"] == 0.8


def test_hybrid_passes_filters_and_candidates():
    class Fake:
        def __init__(self, hits):
            self.hits, self.calls = hits, []

        def search_filings(self, query, k=5, **f):
            self.calls.append((k, f))
            return self.hits[:k]

    d = Fake([{"chunk_id": c, "score": 0.5} for c in "abc"])
    b = Fake([{"chunk_id": c, "score": 5.0} for c in "cde"])
    hits = HybridRetriever(d, b, candidates=30).search_filings("q", ticker="AMD", fiscal_year=2025, k=2)
    assert [h["chunk_id"] for h in hits] == ["c", "a"]
    assert d.calls == b.calls == [(30, {"ticker": "AMD", "fiscal_year": 2025, "item_code": None})]
