"""Qdrant access: collection setup, idempotent upserts, filtered search.

Point IDs are derived from chunk IDs (uuid5), so re-indexing the same chunk
overwrites its point instead of duplicating it.
"""

from __future__ import annotations

import os
import uuid
from typing import Iterable

import numpy as np
from qdrant_client import QdrantClient, models

ID_NAMESPACE = uuid.UUID("6f1c3a52-6a39-4c8e-9a3e-5e2f0f3d9b11")   # fixed: ids must never change
INDEXED_FIELDS = {
    "ticker": models.PayloadSchemaType.KEYWORD,
    "item_code": models.PayloadSchemaType.KEYWORD,
    "accession_no": models.PayloadSchemaType.KEYWORD,
    "fiscal_year": models.PayloadSchemaType.INTEGER,
}


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, chunk_id))


def get_client() -> QdrantClient:
    return QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"), timeout=60)


def ensure_collection(client: QdrantClient, name: str, dim: int) -> bool:
    """Create the collection (cosine distance + payload indexes). Recreate if the
    vector size changed (i.e. a different embedding model). Returns True if created."""
    if client.collection_exists(name):
        if client.get_collection(name).config.params.vectors.size == dim:
            return False
        client.delete_collection(name)
    client.create_collection(name, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
    for field, schema in INDEXED_FIELDS.items():          # indexes make filtered search fast
        client.create_payload_index(name, field_name=field, field_schema=schema)
    return True


def upsert_chunks(client: QdrantClient, name: str, chunks: list[dict], vectors: np.ndarray,
                  batch: int = 256) -> None:
    for i in range(0, len(chunks), batch):
        client.upsert(name, points=[
            models.PointStruct(id=point_id(c["chunk_id"]), vector=v.tolist(), payload=c)
            for c, v in zip(chunks[i:i + batch], vectors[i:i + batch])
        ])


def delete_stale(client: QdrantClient, name: str, keep_chunk_ids: Iterable[str]) -> int:
    """Remove points whose chunk no longer exists (e.g. chunking rules changed)."""
    keep = {point_id(c) for c in keep_chunk_ids}
    stale, offset = [], None
    while True:
        points, offset = client.scroll(name, limit=1000, offset=offset, with_payload=False, with_vectors=False)
        stale += [p.id for p in points if str(p.id) not in keep]
        if offset is None:
            break
    for i in range(0, len(stale), 1000):
        client.delete(name, points_selector=models.PointIdsList(points=stale[i:i + 1000]))
    return len(stale)


def build_filter(ticker=None, fiscal_year=None, item_code=None) -> models.Filter | None:
    """Each argument may be a single value or a list (list = any of)."""
    must = []
    for key, value in (("ticker", ticker), ("fiscal_year", fiscal_year), ("item_code", item_code)):
        if value is None:
            continue
        values = list(value) if isinstance(value, (list, tuple, set)) else [value]
        if key == "fiscal_year":
            values = [int(v) for v in values]
        else:
            values = [str(v).upper() for v in values]
        match = models.MatchValue(value=values[0]) if len(values) == 1 else models.MatchAny(any=values)
        must.append(models.FieldCondition(key=key, match=match))
    return models.Filter(must=must) if must else None


def search(client: QdrantClient, name: str, vector: np.ndarray, k: int = 5, **filters) -> list[dict]:
    res = client.query_points(name, query=vector.tolist(), query_filter=build_filter(**filters),
                              limit=k, with_payload=True)
    return [{"score": p.score, **p.payload} for p in res.points]