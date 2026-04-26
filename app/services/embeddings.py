from __future__ import annotations

from threading import Lock
from typing import Iterable

import numpy as np

from app.config import EMBEDDING_MODEL

_model = None
_model_lock = Lock()


def _get_model():
    """Lazy-load the SentenceTransformer model. The model is ~420MB, so we
    only pull it into memory the first time a report is scored."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")
    vec = _get_model().encode(text, normalize_embeddings=True)
    return np.asarray(vec, dtype=np.float32).tolist()


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    av = np.asarray(list(a), dtype=np.float32)
    bv = np.asarray(list(b), dtype=np.float32)
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom == 0.0:
        return 0.0
    return float(np.dot(av, bv) / denom)
