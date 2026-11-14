"""Build a retriever by name, with settings from configs/retrieval.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
VARIANTS = ("dense", "rerank")


def get_retriever(variant: str = "rerank"):
    if variant not in VARIANTS:
        raise SystemExit(f"unknown retrieval variant {variant!r}; choose from {VARIANTS}")
    from sectra.retrieval.dense import DenseRetriever
    dense = DenseRetriever()
    if variant == "dense":
        return dense

    from sectra.retrieval.reranker import Reranker, RerankRetriever
    cfg = yaml.safe_load(open(ROOT / "configs" / "retrieval.yaml"))
    r = cfg["rerank"]
    return RerankRetriever(dense, Reranker(r["url"], r["model"], r["api_key_env"]),
                           candidates=r["candidates"], default_k=cfg["vector_store"].get("top_k", 5))