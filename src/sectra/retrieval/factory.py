"""Build a retriever by name, with settings from configs/retrieval.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
VARIANTS = ("dense", "bm25", "hybrid")


def get_retriever(variant: str = "dense"):
    cfg = yaml.safe_load(open(ROOT / "configs" / "retrieval.yaml"))
    if variant == "dense":
        from sectra.retrieval.dense import DenseRetriever
        return DenseRetriever()
    if variant in ("bm25", "hybrid"):
        from sectra.retrieval.bm25 import BM25Index
        b = cfg.get("bm25", {})
        bm25 = BM25Index.from_project(ROOT, k1=b.get("k1", 1.2), b=b.get("b", 0.75))
        if variant == "bm25":
            return bm25
        from sectra.retrieval.dense import DenseRetriever
        from sectra.retrieval.hybrid import HybridRetriever
        h = cfg.get("hybrid", {})
        return HybridRetriever(DenseRetriever(), bm25, candidates=h.get("candidates", 30), rrf_k=h.get("rrf_k", 60),
                               default_k=cfg["vector_store"].get("top_k", 5))
    raise SystemExit(f"unknown retrieval variant {variant!r}; choose from {VARIANTS}")
