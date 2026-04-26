"""STUB_AI must let embed() work even when sentence-transformers is
not installed. The Render free-tier deploy depends on this fail-safe."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import builtins
import math

import pytest

from app import config
from app.services.embeddings import EMBEDDING_DIM, _stub_embed, cosine_similarity, embed


def test_stub_returns_correct_dimension():
    v = _stub_embed("anything")
    assert len(v) == EMBEDDING_DIM == 384
    assert all(isinstance(x, float) for x in v)


def test_stub_is_deterministic():
    a = _stub_embed("Tax officer asked for cash")
    b = _stub_embed("Tax officer asked for cash")
    assert a == b


def test_stub_is_normalized():
    """Cosine math depends on unit-length vectors. norm should be ~1.0."""
    v = _stub_embed("anything at all")
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-5


def test_stub_distinguishes_different_text():
    a = _stub_embed("alpha")
    b = _stub_embed("beta")
    sim = cosine_similarity(a, b)
    # Different inputs should NOT collide. Cosine well below 1.0.
    assert sim < 0.5


def test_stub_identical_text_gives_perfect_similarity():
    a = _stub_embed("the same exact sentence here")
    b = _stub_embed("the same exact sentence here")
    sim = cosine_similarity(a, b)
    # Same text → cosine 1.0 (within float tolerance).
    assert abs(sim - 1.0) < 1e-5


def test_embed_with_stub_ai_does_not_import_sentence_transformers(monkeypatch):
    """The whole point of STUB_AI is that the heavy import never happens.
    We assert the module is not in sys.modules after a stubbed embed call,
    and that even if importing it would fail, embed() still works."""
    # Block any attempt to import sentence_transformers.
    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "sentence_transformers" or name.startswith("sentence_transformers."):
            raise ImportError("sentence_transformers banned for this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    monkeypatch.setattr(config, "STUB_AI", True)
    # Reset the singleton so the test doesn't rely on previous-load state.
    import app.services.embeddings as emb_mod
    monkeypatch.setattr(emb_mod, "_model", None)

    v = embed("Tax officer at terminal 7 demanded cash")
    assert len(v) == EMBEDDING_DIM
    assert "sentence_transformers" not in sys.modules


def test_embed_rejects_empty_text(monkeypatch):
    monkeypatch.setattr(config, "STUB_AI", True)
    with pytest.raises(ValueError):
        embed("")
    with pytest.raises(ValueError):
        embed("   ")


def test_singleton_loads_model_once(monkeypatch):
    """When STUB_AI is off, multiple embed() calls share one model load."""
    import app.services.embeddings as emb_mod

    # Switch to non-stub path
    monkeypatch.setattr(config, "STUB_AI", False)
    monkeypatch.setattr(emb_mod, "_model", None)

    load_count = {"n": 0}

    class FakeModel:
        def encode(self, text, normalize_embeddings=False):
            return [0.0] * EMBEDDING_DIM

    def fake_get_model():
        load_count["n"] += 1
        return FakeModel()

    # Patch _get_model itself so we count calls without actually loading.
    monkeypatch.setattr(emb_mod, "_get_model", fake_get_model)

    embed("first call")
    embed("second call")
    embed("third call")

    # Patch above is called every embed, but in the real code _get_model
    # internally short-circuits when _model is set — which is the singleton
    # contract under test in the next assertion against the unpatched fn.
    assert load_count["n"] == 3  # our patched function ran each time

    # Now exercise the real _get_model singleton: first call instantiates,
    # second hits the cached _model and returns immediately.
    monkeypatch.undo()
    monkeypatch.setattr(config, "STUB_AI", False)
    monkeypatch.setattr(emb_mod, "_model", None)

    instantiations = {"n": 0}

    class TrackedModel:
        def __init__(self):
            instantiations["n"] += 1

        def encode(self, text, normalize_embeddings=False):
            import numpy as np
            return np.zeros(EMBEDDING_DIM, dtype="float32")

    # Replace SentenceTransformer at the import boundary so _get_model's
    # `from sentence_transformers import SentenceTransformer` resolves to it.
    fake_module = type(sys)("sentence_transformers")
    fake_module.SentenceTransformer = lambda name: TrackedModel()
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    embed("a")
    embed("b")
    embed("c")
    assert instantiations["n"] == 1, "model was loaded more than once"
