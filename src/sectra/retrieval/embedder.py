"""Embedding model wrapper (BAAI/bge-base-en-v1.5 by default).

bge is trained asymmetrically: passages are embedded as they are, queries get an
instruction prefix. Forgetting the prefix silently lowers retrieval quality.
Vectors are L2-normalised, so cosine similarity is a plain dot product.
"""

from __future__ import annotations

import numpy as np


def pick_device() -> str:
    import torch
    if torch.backends.mps.is_available():     # Apple Silicon GPU
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class Embedder:
    def __init__(self, model_name: str, query_instruction: str = "",
                 device: str | None = None, batch_size: int = 32):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.query_instruction = query_instruction
        self.batch_size = batch_size
        self.device = device or pick_device()
        self.model = SentenceTransformer(model_name, device=self.device)

    def encode_docs(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        vecs = self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=show_progress)
        return np.asarray(vecs, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        return self.encode_docs([self.query_instruction + query])[0]