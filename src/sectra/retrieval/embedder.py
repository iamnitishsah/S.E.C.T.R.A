"""Embedding client for a hosted embeddings API. URL, model and key come from config.

Documents and queries are embedded with different input types (asymmetric model).
Vectors are L2-normalised, so cosine similarity is a plain dot product.
"""

from __future__ import annotations

import os
import time

import numpy as np
import requests


class ContentRejected(Exception):
    """The API refused the input (content screening or validation)."""


class Embedder:
    def __init__(self, cfg: dict, max_retries: int = 6, timeout: float = 120.0):
        key = os.environ.get(cfg["api_key_env"])
        if not key:
            raise RuntimeError(f"{cfg['api_key_env']} is not set")
        self.url = cfg["url"]
        self.model = cfg["model"]
        self.dimensions = cfg["dimensions"]
        self.batch_size = cfg["batch_size"]
        self.doc_type = cfg["doc_input_type"]
        self.query_type = cfg["query_input_type"]
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {key}", "Accept": "application/json"})
        self.rejected = 0
        self.query_cache: dict[str, np.ndarray] = {}

    def _call(self, texts: list[str], input_type: str) -> np.ndarray:
        body = {"model": self.model, "input": texts, "input_type": input_type,
                "dimensions": self.dimensions, "truncate": "END", "encoding_format": "float"}
        for attempt in range(self.max_retries):
            try:
                r = self.session.post(self.url, json=body, timeout=self.timeout)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 200:
                rows = sorted(r.json()["data"], key=lambda d: d["index"])
                vecs = np.asarray([d["embedding"] for d in rows], dtype=np.float32)
                return vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 2 ** attempt)))
                continue
            if r.status_code in (400, 422):
                raise ContentRejected(r.text[:300])
            raise RuntimeError(f"embedding API returned {r.status_code}: {r.text[:300]}")
        raise RuntimeError(f"embedding API still failing after {self.max_retries} attempts")

    def _embed(self, texts: list[str], fallbacks: list[str] | None, input_type: str) -> np.ndarray:
        try:
            return self._call(texts, input_type)
        except ContentRejected as exc:
            if len(texts) > 1:                       # one bad text fails the whole batch: split it
                mid = len(texts) // 2
                fb = fallbacks or [None] * len(texts)
                return np.vstack([self._embed(texts[:mid], fb[:mid], input_type),
                                  self._embed(texts[mid:], fb[mid:], input_type)])
            if fallbacks and fallbacks[0]:
                self.rejected += 1
                return self._call([fallbacks[0]], input_type)
            raise RuntimeError(f"embedding API rejected the input: {exc}") from exc

    def encode_docs(self, texts: list[str], fallbacks: list[str] | None = None) -> np.ndarray:
        """fallbacks[i] is embedded instead of texts[i] if the API refuses texts[i]."""
        out = []
        for i in range(0, len(texts), self.batch_size):
            fb = fallbacks[i:i + self.batch_size] if fallbacks else None
            out.append(self._embed(texts[i:i + self.batch_size], fb, self.doc_type))
        return np.vstack(out)

    def encode_query(self, query: str) -> np.ndarray:
        if query not in self.query_cache:
            self.query_cache[query] = self._embed([query], None, self.query_type)[0]
        return self.query_cache[query]