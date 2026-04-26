"""Cosine-similarity logic is testable without downloading the 420MB model
by stubbing the embedding function. The end-to-end embedding flow is still
exercised manually via the /reports endpoint."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database

test_engine = create_engine("sqlite:///:memory:", future=True)
database.engine = test_engine
database.SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

from app.database import Base, SessionLocal  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.services import duplicate_check  # noqa: E402


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _seed(text: str, vec: list[float]) -> int:
    db = SessionLocal()
    r = Report(user_id=1, text=text, tier=1, embedding=vec)
    db.add(r)
    db.commit()
    db.refresh(r)
    rid = r.id
    db.close()
    return rid


def test_high_similarity_flags_duplicate():
    seeded_vec = [1.0, 0.0, 0.0]
    seeded_id = _seed("bribe at customs window 4", seeded_vec)

    with patch.object(duplicate_check, "embed", return_value=[0.99, 0.01, 0.0]):
        db = SessionLocal()
        result = duplicate_check.check_for_duplicate(db, "near identical text")
        db.close()

    assert result.is_duplicate is True
    assert result.matched_report_id == seeded_id
    assert result.similarity > 0.88


def test_low_similarity_passes():
    _seed("traffic stop bribe", [1.0, 0.0, 0.0])
    with patch.object(duplicate_check, "embed", return_value=[0.0, 1.0, 0.0]):
        db = SessionLocal()
        result = duplicate_check.check_for_duplicate(db, "completely different topic")
        db.close()
    assert result.is_duplicate is False
    assert result.matched_report_id is None
