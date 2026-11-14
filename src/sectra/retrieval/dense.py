"""
Dense retrieval: question -> bge query vector -> filtered Qdrant search.

    from sectra.retrieval.dense import DenseRetriever
    r = DenseRetriever()
    r.search_filings("export restrictions to China", ticker="NVDA", fiscal_year=2025, item_code="1A")
"""

from __future__ import annotations

from pathlib import Path

import yaml

from sectra.retrieval.embedder import Embedder
from sectra.storage import vector_store

ROOT = Path(__file__).resolve().parents[3]


class DenseRetriever:
    def __init__(self, client=None, embedder: Embedder | None = None):
        cfg = yaml.safe_load(open(ROOT / "configs" / "retrieval.yaml"))
        self.collection = cfg["vector_store"]["collection"]
        self.default_k = cfg["vector_store"].get("top_k", 5)
        self.client = client or vector_store.get_client()
        e = cfg["embedding"]
        self.embedder = embedder or Embedder(cfg["embedding"])

    def search_filings(self, query: str, ticker=None, fiscal_year=None, item_code=None,
                       k: int | None = None) -> list[dict]:
        """Top-k chunks for a question, optionally filtered by company, year and Item."""
        vec = self.embedder.encode_query(query)
        return vector_store.search(self.client, self.collection, vec, k or self.default_k,
                                   ticker=ticker, fiscal_year=fiscal_year, item_code=item_code)