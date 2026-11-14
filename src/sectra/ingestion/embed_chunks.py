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
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]


def embed_text(chunk: dict) -> str:
    return chunk["header"] + "\n" + chunk["text"]       # the header is embedded with the text


def embedding_dir(root: Path, cfg: dict) -> Path:
    name = f"{cfg['model'].replace('/', '__')}__{cfg['dimensions']}"
    return root / "data/processed/embeddings" / name


def cache_key(cfg: dict, text: str) -> str:
    return hashlib.sha1(f"{cfg['model']}\n{cfg['dimensions']}\n{text}".encode("utf-8")).hexdigest()


def save_cache(out: Path, cached: dict[str, np.ndarray]) -> None:
    ks = list(cached)
    np.save(out / "cache_vectors.npy", np.stack([cached[k] for k in ks]).astype(np.float32))
    (out / "cache_keys.json").write_text(json.dumps(ks))


def run(root: Path, make_embedder, checkpoint_every: int = 20) -> np.ndarray:
    cfg = yaml.safe_load(open(root / "configs" / "retrieval.yaml"))["embedding"]
    with open(root / "data/processed/chunks/chunks.jsonl", encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh]
    out = embedding_dir(root, cfg)
    out.mkdir(parents=True, exist_ok=True)

    keys = [cache_key(cfg, embed_text(c)) for c in chunks]
    cached: dict[str, np.ndarray] = {}
    if (out / "cache_vectors.npy").exists() and (out / "cache_keys.json").exists():
        cached = dict(zip(json.loads((out / "cache_keys.json").read_text()),
                          np.load(out / "cache_vectors.npy")))

    todo = [i for i, k in enumerate(keys) if k not in cached]
    print(f"{len(chunks):,} chunks | cached {len(chunks) - len(todo):,} | to embed {len(todo):,}")
    if todo:
        emb = make_embedder(cfg)
        step, workers = cfg["batch_size"], cfg.get("workers", 1)
        batches = [todo[s:s + step] for s in range(0, len(todo), step)]

        def work(idx: list[int]):
            vecs = emb.encode_docs([embed_text(chunks[i]) for i in idx],
                                   fallbacks=[chunks[i]["header"] for i in idx])
            return idx, vecs

        t0, done = time.monotonic(), 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(work, b) for b in batches]
            try:
                for n, fut in enumerate(as_completed(futures), 1):
                    idx, vecs = fut.result()
                    for i, v in zip(idx, vecs):
                        cached[keys[i]] = v
                    done += len(idx)
                    if n % checkpoint_every == 0:
                        save_cache(out, cached)
                        print(f"  {done:,}/{len(todo):,}  ({done / (time.monotonic() - t0):.0f}/s)", flush=True)
            finally:
                for f in futures:          # on an error or Ctrl-C, drop the batches not started yet
                    f.cancel()
                save_cache(out, cached)    # and keep everything finished so far
        print(f"embedded {len(todo):,} chunks in {time.monotonic() - t0:.0f}s with {workers} workers | "
              f"{emb.rejected} refused, embedded from header only")

    vectors = np.stack([cached[k] for k in keys]).astype(np.float32)
    np.save(out / "vectors.npy", vectors)
    (out / "keys.json").write_text(json.dumps(keys))
    (out / "chunk_ids.json").write_text(json.dumps([c["chunk_id"] for c in chunks]))
    print(f"saved {vectors.shape[0]:,} x {vectors.shape[1]} -> {out.relative_to(root)}")
    return vectors


def main() -> None:  # pragma: no cover - calls the embedding API
    from dotenv import load_dotenv
    from sectra.retrieval.embedder import Embedder
    load_dotenv(ROOT / ".env")
    run(ROOT, Embedder)

if __name__ == "__main__":
    main()