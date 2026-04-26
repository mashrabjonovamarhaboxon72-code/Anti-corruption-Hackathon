import os
import sys
from pathlib import Path

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database
from app.config import DEFAULT_RELIABILITY_INDEX

# Re-bind engine to in-memory SQLite for the test (Postgres not required).
test_engine = create_engine("sqlite:///:memory:", future=True)
database.engine = test_engine
database.SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

from app.database import Base, SessionLocal  # noqa: E402
from app.models.audit_ledger import AuditLedger  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.scoring import CORRUPTION_TIERS, award_points  # noqa: E402


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _new_user(ri: int) -> User:
    db = SessionLocal()
    user = User(pseudonymous_token=f"pt_{ri}_{os.urandom(4).hex()}".ljust(64, "0")[:64], reliability_index=ri)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _new_report(user_id: int, tier: int) -> Report:
    db = SessionLocal()
    report = Report(user_id=user_id, text="x" * 20, tier=tier, embedding=[0.0])
    db.add(report)
    db.commit()
    db.refresh(report)
    db.close()
    return report


def test_baseline_user_gets_1x_multiplier():
    user = _new_user(DEFAULT_RELIABILITY_INDEX)
    report = _new_report(user.id, tier=2)

    db = SessionLocal()
    user = db.get(User, user.id)
    award = award_points(db, user=user, report_id=report.id, tier=2)
    db.close()

    assert award.ri_multiplier == 1.0
    assert award.awarded_points == CORRUPTION_TIERS[2]  # 250


def test_high_ri_user_gets_2x():
    user = _new_user(1000)
    report = _new_report(user.id, tier=4)
    db = SessionLocal()
    user = db.get(User, user.id)
    award = award_points(db, user=user, report_id=report.id, tier=4)
    db.close()
    assert award.ri_multiplier == 2.0
    assert award.awarded_points == 2000


def test_low_ri_user_gets_fractional():
    user = _new_user(125)
    report = _new_report(user.id, tier=3)
    db = SessionLocal()
    user = db.get(User, user.id)
    award = award_points(db, user=user, report_id=report.id, tier=3)
    db.close()
    assert award.ri_multiplier == 0.25
    assert award.awarded_points == 125  # 500 * 0.25


def test_audit_ledger_is_append_only():
    user = _new_user(500)
    report = _new_report(user.id, tier=1)
    db = SessionLocal()
    user = db.get(User, user.id)
    award_points(db, user=user, report_id=report.id, tier=1)

    entry = db.query(AuditLedger).filter(AuditLedger.report_id == report.id).one()
    entry.awarded_points = 99999
    with pytest.raises(PermissionError):
        db.commit()
    db.rollback()

    db.delete(entry)
    with pytest.raises(PermissionError):
        db.commit()
    db.rollback()
    db.close()


def test_unknown_tier_rejected():
    user = _new_user(500)
    report = _new_report(user.id, tier=1)
    db = SessionLocal()
    user = db.get(User, user.id)
    with pytest.raises(ValueError):
        award_points(db, user=user, report_id=report.id, tier=99)
    db.close()
