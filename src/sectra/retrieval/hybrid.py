"""Hybrid retrieval: dense + BM25, merged with Reciprocal Rank Fusion (RRF).

    fused score(chunk) = sum over the two searches of 1 / (rrf_k + rank in that search)

RRF uses only ranks, so cosine scores (0-1) and BM25 scores (0-40+) never have to be
put on one scale. A chunk ranked well by both searches beats one ranked first by only one.
"""

from __future__ import annotations


def rrf_fuse(ranked_lists: dict[str, list[dict]], rrf_k: int = 60) -> list[dict]:
    fused: dict[str, dict] = {}
    for name, hits in ranked_lists.items():
        for rank, h in enumerate(hits, start=1):
            e = fused.setdefault(h["chunk_id"], {**h, "score": 0.0, "ranks": {}})
            e["score"] += 1.0 / (rrf_k + rank)
            e["ranks"][name] = rank                 # kept for the trace: who found this chunk
            e[f"{name}_score"] = h["score"]
    return sorted(fused.values(), key=lambda e: (-e["score"], e["chunk_id"]))


class HybridRetriever:
    def __init__(self, dense, bm25, candidates: int = 30, rrf_k: int = 60, default_k: int = 5):
        self.dense, self.bm25 = dense, bm25
        self.candidates, self.rrf_k, self.default_k = candidates, rrf_k, default_k

    def candidate_pool(self, query: str, ticker=None, fiscal_year=None, item_code=None) -> list[dict]:
        """Everything either search put in its top `candidates`, in fused order (at most 2 x candidates)."""
        f = {"ticker": ticker, "fiscal_year": fiscal_year, "item_code": item_code}
        return rrf_fuse({
            "dense": self.dense.search_filings(query, k=self.candidates, **f),
            "bm25": self.bm25.search_filings(query, k=self.candidates, **f),
        }, self.rrf_k)

    def search_filings(self, query: str, ticker=None, fiscal_year=None, item_code=None, k: int | None = None) -> list[dict]:
        f = {"ticker": ticker, "fiscal_year": fiscal_year, "item_code": item_code}
        n = max(self.candidates, k or self.default_k)
        lists = {
            "dense": self.dense.search_filings(query, k=n, **f),
            "bm25": self.bm25.search_filings(query, k=n, **f),
        }
        return rrf_fuse(lists, self.rrf_k)[: k or self.default_k]
