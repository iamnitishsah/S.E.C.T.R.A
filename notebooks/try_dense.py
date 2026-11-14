"""
sanity check: brute-force search over the cached vectors (no Qdrant yet).
    python notebooks/try_dense.py
    python notebooks/try_dense.py "your own question"
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml

from sectra.retrieval.embedder import Embedder

cfg = yaml.safe_load(open("configs/retrieval.yaml"))["embedding"]
d = Path("data/processed/embeddings") / cfg["model"].replace("/", "__")
V = np.load(d / "vectors.npy")
chunks = [json.loads(l) for l in open("data/processed/chunks/chunks.jsonl", encoding="utf-8")]
assert len(chunks) == len(V), "chunks.jsonl changed since embedding: run make embed"
emb = Embedder(cfg["model"], cfg["query_instruction"])

QUERIES = [
    ("export restrictions on advanced AI chips to China", {}),
    ("reliance on a single foundry to manufacture our wafers", {}),
    ("Medicare drug price negotiation under the Inflation Reduction Act", {}),
    ("climate change laws and greenhouse gas emission regulation", {}),
    ("what drove the increase in data center revenue", {"ticker": "NVDA", "item_code": "7"}),
]
queries = [(q, {}) for q in sys.argv[1:]] or QUERIES

for q, filt in queries:
    mask = np.array([all(c[k] == v for k, v in filt.items()) for c in chunks])
    scores = V @ emb.encode_query(q)           # cosine similarity (vectors are normalised)
    scores[~mask] = -np.inf                    # metadata filter
    print(f"\n{q}  {filt or ''}")
    for i in np.argsort(-scores)[:5]:
        c = chunks[i]
        print(f"  {scores[i]:.3f}  {c['chunk_id']:32}  {c['header'][:75]}")