"""Cross-encoder reranking through a hosted reranking API.

The embedding model reads question and passage separately and compares two vectors.
A cross-encoder reads them together and outputs one relevance score, which is more
accurate but far slower, so it only re-sorts the top candidates from dense search.
Scores are passed through a sigmoid: 0 = irrelevant, 1 = clearly answers the question.

The URL, model name and API-key variable all come from configs/retrieval.yaml.
Expected API format: request {model, query: {text}, passages: [{text}], truncate},
response {rankings: [{index, logit}]}.
"""

from __future__ import annotations

import math
import os
import time


class ContentRejected(Exception):
    """The API's content-safety filter refused a request."""


class Reranker:
    def __init__(self, url: str, model: str, api_key_env: str,
                 max_retries: int = 5, timeout: float = 90.0):
        import requests
        key = os.getenv(api_key_env)
        if not key:
            raise RuntimeError(f"{api_key_env} is not set (add it to .env)")
        self.url, self.model, self.max_retries, self.timeout = url, model, max_retries, timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {key}", "Accept": "application/json"})
        self.cache: dict[tuple[str, str], float] = {}     # (question, chunk_id) -> score
        self.rejected = 0                                 # passages the safety filter refused to score

    def _call(self, query: str, texts: list[str]) -> list[float]:
        body = {"model": self.model, "query": {"text": query},
                "passages": [{"text": t} for t in texts], "truncate": "END"}
        for attempt in range(self.max_retries):
            r = self.session.post(self.url, json=body, timeout=self.timeout)
            if r.status_code == 200:
                scores = [0.0] * len(texts)
                for item in r.json()["rankings"]:                  # each: {"index": i, "logit": x}
                    logit = max(-50.0, min(50.0, float(item["logit"])))
                    scores[item["index"]] = 1.0 / (1.0 + math.exp(-logit))
                return scores
            if r.status_code == 422 and "safety" in r.text.lower():
                raise ContentRejected(r.text[:200])
            if r.status_code in (429, 500, 502, 503, 504):         # rate limit or server trouble: wait, retry
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"rerank API returned {r.status_code}: {r.text[:300]}")
        raise RuntimeError(f"rerank API still failing after {self.max_retries} attempts")

    def _score_texts(self, query: str, texts: list[str]) -> list[float]:
        """The filter rejects a whole batch for one passage: split until that passage is isolated."""
        try:
            return self._call(query, texts)
        except ContentRejected:
            if len(texts) == 1:
                self.rejected += 1
                return [0.0]                                       # cannot be scored: ranked last
            mid = len(texts) // 2
            return self._score_texts(query, texts[:mid]) + self._score_texts(query, texts[mid:])

    def score(self, query: str, hits: list[dict]) -> list[float]:
        """One relevance score per hit, in the same order. Cached per (question, chunk)."""
        todo = [h for h in hits if (query, h["chunk_id"]) not in self.cache]
        if todo:
            texts = [h["header"] + "\n" + h["text"] for h in todo]
            for h, s in zip(todo, self._score_texts(query, texts)):
                self.cache[(query, h["chunk_id"])] = s
        return [self.cache[(query, h["chunk_id"])] for h in hits]


class RerankRetriever:
    """The top `candidates` chunks from dense search, re-sorted by the cross-encoder."""

    def __init__(self, dense, reranker, candidates: int, default_k: int = 5):
        self.dense, self.reranker, self.candidates, self.default_k = dense, reranker, candidates, default_k
        self.last_pool: list[str] = []                    # candidate chunk ids of the last search (for the eval)

    def search_filings(self, query: str, ticker=None, fiscal_year=None, item_code=None, k: int | None = None) -> list[dict]:
        pool = self.dense.search_filings(query, ticker=ticker, fiscal_year=fiscal_year, item_code=item_code,
                                         k=self.candidates)
        self.last_pool = [h["chunk_id"] for h in pool]
        scores = self.reranker.score(query, pool)
        ranked = sorted(zip(scores, pool), key=lambda pair: -pair[0])
        return [{**h, "dense_score": h["score"], "score": s} for s, h in ranked[: k or self.default_k]]