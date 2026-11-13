"""Embed every chunk, caching vectors so re-runs only embed new or changed chunks.

    python -m sectra.ingestion.embed_chunks

Output in data/processed/embeddings/<model>/:
  vectors.npy     N x dim float32, same order as chunks.jsonl
  chunk_ids.json  chunk_id for each row
  keys.json       content hash per row (model + embedded text); the cache key
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]


def embed_text(chunk: dict) -> str:
    return chunk["header"] + "\n" + chunk["text"]       # the header is embedded with the text


def cache_key(model: str, text: str) -> str:
    return hashlib.sha1(f"{model}\n{text}".encode("utf-8")).hexdigest()


def run(root: Path, make_embedder) -> np.ndarray:
    cfg = yaml.safe_load(open(root / "configs" / "retrieval.yaml"))["embedding"]
    with open(root / "data/processed/chunks/chunks.jsonl", encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh]
    out = root / "data/processed/embeddings" / cfg["model"].replace("/", "__")
    out.mkdir(parents=True, exist_ok=True)

    keys = [cache_key(cfg["model"], embed_text(c)) for c in chunks]
    cached: dict[str, np.ndarray] = {}
    if (out / "vectors.npy").exists() and (out / "keys.json").exists():
        old_vectors = np.load(out / "vectors.npy")
        old_keys = json.loads((out / "keys.json").read_text())
        cached = dict(zip(old_keys, old_vectors))

    todo = [i for i, k in enumerate(keys) if k not in cached]
    print(f"{len(chunks):,} chunks | cached {len(chunks) - len(todo):,} | to embed {len(todo):,}")
    if todo:
        emb = make_embedder(cfg)
        print(f"model {cfg['model']} on {emb.device}")
        t0 = time.monotonic()
        new = emb.encode_docs([embed_text(chunks[i]) for i in todo], show_progress=True)
        for i, v in zip(todo, new):
            cached[keys[i]] = v
        secs = time.monotonic() - t0
        print(f"embedded {len(todo):,} chunks in {secs:.0f}s ({len(todo) / max(secs, 1e-9):.0f}/s)")

    vectors = np.stack([cached[k] for k in keys]).astype(np.float32)
    np.save(out / "vectors.npy", vectors)
    (out / "keys.json").write_text(json.dumps(keys))
    (out / "chunk_ids.json").write_text(json.dumps([c["chunk_id"] for c in chunks]))
    print(f"saved {vectors.shape[0]:,} x {vectors.shape[1]} -> {out.relative_to(root)}")
    return vectors


def main() -> None:  # pragma: no cover - downloads the model
    from sectra.retrieval.embedder import Embedder
    run(ROOT, lambda cfg: Embedder(cfg["model"], cfg["query_instruction"], batch_size=cfg["batch_size"]))


if __name__ == "__main__":
    main()