import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database

test_engine = create_engine("sqlite:///:memory:", future=True)
database.engine = test_engine
database.SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

from app.database import Base, SessionLocal  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.badges import (  # noqa: E402
    CORRUPTION_FIGHTER_BADGE,
    compute_badges,
    verified_high_tier_count,
)


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _user() -> User:
    db = SessionLocal()
    u = User(pseudonymous_token=os.urandom(32).hex(), age_tier="Adult")
    db.add(u); db.commit(); db.refresh(u); db.close()
    return u


def _report(user_id: int, *, tier: int, verdict: str | None):
    db = SessionLocal()
    r = Report(
        user_id=user_id,
        text="x" * 20,
        tier=tier,
        embedding=[0.0],
        verification_status=verdict,
    )
    db.add(r); db.commit(); db.close()


def test_no_badge_below_threshold():
    u = _user()
    for _ in range(3):
        _report(u.id, tier=3, verdict="Verified")
    db = SessionLocal()
    badges = compute_badges(db, db.get(User, u.id))
    db.close()
    assert badges == []


def test_badge_awarded_at_four_verified_tier3():
    u = _user()
    for _ in range(4):
        _report(u.id, tier=3, verdict="Verified")
    db = SessionLocal()
    badges = compute_badges(db, db.get(User, u.id))
    db.close()
    assert len(badges) == 1
    assert badges[0]["id"] == CORRUPTION_FIGHTER_BADGE["id"]
    assert badges[0]["earned_count"] == 4


def test_badge_counts_tier4_too():
    u = _user()
    _report(u.id, tier=3, verdict="Verified")
    _report(u.id, tier=4, verdict="Verified")
    _report(u.id, tier=4, verdict="Verified")
    _report(u.id, tier=3, verdict="Verified")
    db = SessionLocal()
    assert verified_high_tier_count(db, db.get(User, u.id)) == 4
    db.close()


def test_unverified_or_low_tier_dont_count():
    u = _user()
    for _ in range(5):
        _report(u.id, tier=3, verdict=None)  # not verified
    for _ in range(5):
        _report(u.id, tier=2, verdict="Verified")  # too low tier
    for _ in range(5):
        _report(u.id, tier=4, verdict="Malicious")  # not verified
    db = SessionLocal()
    badges = compute_badges(db, db.get(User, u.id))
    db.close()
    assert badges == []
