import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, database

test_engine = create_engine(
    "sqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
test_session_factory = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.evidence import Evidence  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.demo_seed import (  # noqa: E402
    BASELINE_REPORTS,
    WHISTLEBLOWER_NATIONAL_ID,
    WHISTLEBLOWER_RI,
    reset_database,
    seed_demo_state,
)

SessionLocal = test_session_factory


def _fake_embedder(text: str) -> list[float]:
    """Deterministic fake embedding so tests don't load the 420MB model."""
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    # Repeat into 768 floats in [0, 1)
    raw = (h * (768 // len(h) + 1))[:768]
    return [b / 255.0 for b in raw]


def setup_module(module):
    database.engine = test_engine
    database.SessionLocal = test_session_factory
    Base.metadata.create_all(bind=test_engine)


def setup_function(function):
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()
    config.DEMO_MODE = False  # explicit per-test default


# ---- service tests ----


def test_reset_database_clears_every_table():
    db = SessionLocal()
    db.add(User(pseudonymous_token="x" * 64, age_tier="Adult", reliability_index=500))
    db.commit()
    db.close()

    db = SessionLocal()
    counts = reset_database(db)
    db.close()

    assert counts["users"] == 1
    db = SessionLocal()
    assert db.query(User).count() == 0
    db.close()


def test_reset_database_unlinks_evidence_files(tmp_path, monkeypatch):
    # Re-route uploads to a tmp dir so we don't touch the real one.
    from app import config as cfg
    from app.services import image_sanitizer

    monkeypatch.setattr(cfg, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(image_sanitizer, "UPLOAD_DIR", tmp_path)

    db = SessionLocal()
    state = seed_demo_state(db, embedder=_fake_embedder)
    file_path = Path(state["evidence"]["file_path"])
    assert file_path.exists()
    db.close()

    db = SessionLocal()
    reset_database(db)
    db.close()

    assert not file_path.exists()


def test_seed_creates_whistleblower_with_session_and_mnemonic():
    db = SessionLocal()
    state = seed_demo_state(db, embedder=_fake_embedder)
    db.close()

    wb = state["whistleblower"]
    assert wb["national_id"] == WHISTLEBLOWER_NATIONAL_ID
    assert wb["reliability_index"] == WHISTLEBLOWER_RI
    assert wb["age_tier"] == "Adult"
    assert len(wb["recovery_mnemonic"].split()) == 24
    assert len(wb["session_token"]) >= 32

    db = SessionLocal()
    sess = db.query(SessionModel).filter(SessionModel.session_token == wb["session_token"]).one()
    assert sess.pseudonymous_token == wb["pseudonymous_token"]
    db.close()


def test_seed_creates_three_baselines_in_distinct_departments():
    db = SessionLocal()
    state = seed_demo_state(db, embedder=_fake_embedder)
    db.close()

    bls = state["baseline_reports"]
    assert len(bls) == 3
    depts = {b["department"] for b in bls}
    assert len(depts) == 3
    assert depts == {b["department"] for b in BASELINE_REPORTS}


def test_seed_creates_evidence_with_integrity_hash(tmp_path, monkeypatch):
    from app import config as cfg
    from app.services import image_sanitizer

    monkeypatch.setattr(cfg, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(image_sanitizer, "UPLOAD_DIR", tmp_path)

    db = SessionLocal()
    state = seed_demo_state(db, embedder=_fake_embedder)
    db.close()

    ev = state["evidence"]
    assert len(ev["integrity_hash"]) == 64
    assert ev["metadata_stripped"] is True
    assert ev["size_bytes"] < ev["original_bytes"]  # cleansed file is smaller (no EXIF)

    db = SessionLocal()
    rows = db.query(Evidence).all()
    assert len(rows) == 1
    assert rows[0].integrity_hash == ev["integrity_hash"]
    db.close()


def test_seed_is_idempotent_when_called_after_reset():
    db = SessionLocal()
    seed_demo_state(db, embedder=_fake_embedder)
    db.close()

    db = SessionLocal()
    reset_database(db)
    seed_demo_state(db, embedder=_fake_embedder)
    db.close()

    db = SessionLocal()
    assert db.query(User).count() == 1
    assert db.query(Report).count() == 3
    assert db.query(Evidence).count() == 1
    db.close()


# ---- endpoint tests ----


def test_endpoint_refuses_when_demo_mode_off():
    config.DEMO_MODE = False
    with TestClient(app) as c:
        # Both methods rejected the same way when DEMO_MODE is off.
        r_post = c.post("/admin/demo-setup")
        r_get = c.get("/admin/demo-setup")
    for r in (r_post, r_get):
        assert r.status_code == 403
        assert "DEMO_MODE" in r.json()["detail"]


def test_endpoint_accepts_get_in_addition_to_post(tmp_path, monkeypatch):
    """A presenter should be able to fire demo-setup from the address bar
    in the middle of a demo. GET and POST must yield the same fresh state."""
    from app import config as cfg
    from app.services import image_sanitizer

    monkeypatch.setattr(cfg, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(image_sanitizer, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("app.services.embeddings.embed", _fake_embedder)

    config.DEMO_MODE = True
    with TestClient(app) as c:
        r = c.get("/admin/demo-setup")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["demo_state"]["whistleblower"]["reliability_index"] == 950
    assert len(body["demo_state"]["baseline_reports"]) == 3
    # Cache-Control must forbid the back-button from re-firing the wipe
    # via a cached "ok" response.
    assert "no-store" in r.headers.get("cache-control", "").lower()


def test_endpoint_runs_when_demo_mode_on(tmp_path, monkeypatch):
    from app import config as cfg
    from app.services import image_sanitizer

    monkeypatch.setattr(cfg, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(image_sanitizer, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("app.services.demo_seed.sanitize_and_store",
                        image_sanitizer.sanitize_and_store)
    # Also patch the embedder lookup so the endpoint doesn't load 420MB.
    monkeypatch.setattr("app.services.embeddings.embed", _fake_embedder)

    config.DEMO_MODE = True
    with TestClient(app) as c:
        r = c.post("/admin/demo-setup")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "demo_state" in body
    assert "cleared" in body
    assert body["demo_state"]["whistleblower"]["reliability_index"] == 950
    assert len(body["demo_state"]["baseline_reports"]) == 3
    assert "warning" in body


def test_endpoint_wipes_existing_data(tmp_path, monkeypatch):
    from app import config as cfg
    from app.services import image_sanitizer

    monkeypatch.setattr(cfg, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(image_sanitizer, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("app.services.embeddings.embed", _fake_embedder)

    # Pre-seed a "real" user that should disappear after demo-setup
    db = SessionLocal()
    db.add(User(pseudonymous_token="z" * 64, age_tier="Senior", reliability_index=300))
    db.commit()
    db.close()

    config.DEMO_MODE = True
    with TestClient(app) as c:
        c.post("/admin/demo-setup")

    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    # Only the Whistleblower remains; the pre-existing user is gone.
    assert len(users) == 1
    assert users[0].reliability_index == 950
