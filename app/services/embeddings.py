"""Text → embedding service.

Two paths through embed():

  Real path  — lazy-loads sentence-transformers/all-MiniLM-L6-v2 the first
               time a report is scored. The model + torch eat ~330 MB of
               RAM but produce true semantic embeddings, so the duplicate-
               check service catches reworded variants ("bribe at customs"
               vs "officer asked for cash" → ~0.7 similarity).

  Stub path  — when STUB_AI=1, embed() returns a deterministic 384-dim
               unit vector keyed by SHA-256(text). Same text → identical
               vector → cosine similarity = 1.0 (exact-duplicate detection
               still works). Different text → orthogonal-ish vectors →
               cosine ≈ 0 (semantic near-duplicates no longer caught).
               Fail-safe for the Render free-tier 512 MB cap.

The model loader is a textbook double-checked-locking singleton: one
SentenceTransformer per process, regardless of how many concurrent
first-requests race the loader.
"""

from __future__ import annotations

import hashlib
from threading import Lock
from typing import Iterable

import numpy as np

from app import config

# Match all-MiniLM-L6-v2's output dimensionality so swapping STUB_AI off
# doesn't require re-embedding existing reports — they remain shape-
# compatible with the real model's vectors.
EMBEDDING_DIM = 384


# ── Singleton state ────────────────────────────────────────────────
_model = None
_model_lock = Lock()


def _get_model():
    """Singleton accessor — exactly one SentenceTransformer per process.

    Double-checked locking pattern: the fast path (model already loaded)
    avoids the lock entirely; the slow path acquires the lock and re-checks
    so concurrent first-requests don't trigger N parallel model loads.
    """
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


# ── Stub embedding ─────────────────────────────────────────────────
def _stub_embed(text: str) -> list[float]:
    """Deterministic EMBEDDING_DIM-vector keyed by SHA-256(text).

    Hashes are repeated to fill EMBEDDING_DIM bytes, then mapped from
    [0, 255] → [-0.5, +0.5] floats and L2-normalized so cosine similarity
    behaves sensibly (range [-1, 1]).
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    raw = (h * (EMBEDDING_DIM // len(h) + 1))[:EMBEDDING_DIM]
    vec = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 255.0 - 0.5
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        return [0.0] * EMBEDDING_DIM
    return (vec / norm).tolist()


# ── Public API ─────────────────────────────────────────────────────
def embed(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")
    # Read STUB_AI via the config module reference (not a top-level import)
    # so tests can flip it via monkeypatch.setattr(config, "STUB_AI", True).
    if config.STUB_AI:
        return _stub_embed(text)
    vec = _get_model().encode(text, normalize_embeddings=True)
    return np.asarray(vec, dtype=np.float32).tolist()


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    av = np.asarray(list(a), dtype=np.float32)
    bv = np.asarray(list(b), dtype=np.float32)
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom == 0.0:
        return 0.0
    return float(np.dot(av, bv) / denom)
