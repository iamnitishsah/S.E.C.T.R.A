"""
Load chunks + cached vectors into Qdrant.

    python -m sectra.ingestion.index_chunks

Idempotent: point IDs come from chunk IDs, and points for chunks that no
longer exist are deleted, so the collection always mirrors chunks.jsonl.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]


def run(root: Path, client) -> int:
    from sectra.storage.vector_store import delete_stale, ensure_collection, upsert_chunks
    from sectra.ingestion.embed_chunks import embedding_dir

    cfg = yaml.safe_load(open(root / "configs" / "retrieval.yaml"))
    name = cfg["vector_store"]["collection"]
    emb_dir = embedding_dir(root, cfg["embedding"])

    with open(root / "data/processed/chunks/chunks.jsonl", encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh]
    vectors = np.load(emb_dir / "vectors.npy")
    ids = json.loads((emb_dir / "chunk_ids.json").read_text())
    if ids != [c["chunk_id"] for c in chunks]:
        raise SystemExit("Embeddings are out of date with chunks.jsonl: run `make embed` first.")

    t0 = time.monotonic()
    created = ensure_collection(client, name, vectors.shape[1])
    upsert_chunks(client, name, chunks, vectors)
    removed = delete_stale(client, name, ids)
    total = client.count(name, exact=True).count
    print(f"collection '{name}' ({'created' if created else 'existing'}): upserted {len(chunks):,}, "
          f"removed {removed:,} stale, total {total:,} points in {time.monotonic() - t0:.0f}s")
    return total


def main() -> None:  # pragma: no cover - needs a running Qdrant
    from dotenv import load_dotenv

    from sectra.storage.vector_store import get_client
    load_dotenv(ROOT / ".env")
    run(ROOT, get_client())


if __name__ == "__main__":
    main()