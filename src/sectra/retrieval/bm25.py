"""BM25 keyword search over the chunks (the classic ranking function behind search engines).

    score(question, chunk) = sum over question words w that appear in the chunk of
        idf(w) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * chunk_length / average_length))

  tf   how often w appears in the chunk (more is better, with diminishing returns: k1)
  idf  how rare w is across all chunks (a rare word like "Winrevair" counts far more than "revenue")
  b    how strongly long chunks are penalised

Dense search matches meaning; BM25 matches exact terms (years, product names, tickers).
The index lives in memory and is rebuilt from chunks.jsonl at start-up (a few seconds).
"""

from __future__ import annotations

import csv
import json
import math
import re
from array import array
from collections import Counter
from pathlib import Path

import numpy as np

TOKEN_RE = re.compile(r"[a-z]+|\d+(?:\.\d+)?")
THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3})")


def tokenize(text: str) -> list[str]:
    """Lowercase words and numbers. 'FY2025' -> fy, 2025; '30,390' -> 30390; plural 's' removed."""
    text = THOUSANDS_RE.sub("", text.lower())
    out = []
    for tok in TOKEN_RE.findall(text):
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]                      # risks -> risk, obligations -> obligation
        out.append(tok)
    return out


class BM25Index:
    def __init__(self, chunks: list[dict], names: dict[str, str] | None = None, k1: float = 1.2, b: float = 0.75):
        self.chunks, self.k1 = chunks, k1
        names = names or {}
        n = len(chunks)
        lengths = np.zeros(n, dtype=np.float32)
        ids: dict[str, array] = {}
        tfs: dict[str, array] = {}
        for i, c in enumerate(chunks):
            # Company name is indexed too: questions say "Apple", chunk text says "the Company".
            tokens = tokenize(f"{c['ticker']} {names.get(c['ticker'], '')} {c['header']}\n{c['text']}")
            lengths[i] = len(tokens)
            for term, tf in Counter(tokens).items():
                ids.setdefault(term, array("i")).append(i)
                tfs.setdefault(term, array("f")).append(tf)
        self.length_norm = k1 * (1 - b + b * lengths / max(float(lengths.mean()) if n else 1.0, 1.0))
        self.postings = {t: (np.frombuffer(ids[t], dtype=np.int32), np.frombuffer(tfs[t], dtype=np.float32)) for t in ids}
        self.idf = {t: math.log(1 + (n - len(d) + 0.5) / (len(d) + 0.5)) for t, (d, _) in self.postings.items()}
        self.meta = {
            "ticker": np.array([c["ticker"] for c in chunks]),
            "fiscal_year": np.array([int(c["fiscal_year"]) for c in chunks]),
            "item_code": np.array([c["item_code"] for c in chunks]),
        }

    @classmethod
    def from_project(cls, root: Path, **kw) -> "BM25Index":
        with open(root / "data/processed/chunks/chunks.jsonl", encoding="utf-8") as fh:
            chunks = [json.loads(line) for line in fh]
        names, manifest = {}, root / "data/raw/manifest/companies.csv"
        if manifest.exists():
            with open(manifest, newline="") as fh:
                names = {r["ticker"]: r["name"] for r in csv.DictReader(fh)}
        return cls(chunks, names, **kw)

    def scores(self, query: str) -> np.ndarray:
        s = np.zeros(len(self.chunks), dtype=np.float32)
        for term in set(tokenize(query)):
            if term in self.postings:
                doc_ids, tf = self.postings[term]
                s[doc_ids] += self.idf[term] * tf * (self.k1 + 1) / (tf + self.length_norm[doc_ids])
        return s

    def _mask(self, **filters) -> np.ndarray | None:
        mask = None
        for key, value in filters.items():
            if value is None:
                continue
            values = list(value) if isinstance(value, (list, tuple, set)) else [value]
            values = [int(v) for v in values] if key == "fiscal_year" else [str(v).upper() for v in values]
            m = np.isin(self.meta[key], values)
            mask = m if mask is None else mask & m
        return mask

    def search_filings(self, query: str, ticker=None, fiscal_year=None, item_code=None, k: int = 5) -> list[dict]:
        """Same interface and filters as DenseRetriever.search_filings."""
        s = self.scores(query)
        mask = self._mask(ticker=ticker, fiscal_year=fiscal_year, item_code=item_code)
        if mask is not None:
            s = np.where(mask, s, 0.0)
        top = np.argsort(-s, kind="stable")[:k]
        return [{"score": float(s[i]), **self.chunks[i]} for i in top if s[i] > 0]
