import os
import sys
from pathlib import Path

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
from app.models.audit_ledger import AuditLedger  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.reliability import RI_MAX, RI_MIN, recalculate_pending  # noqa: E402


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _seed(ri: int, verdict: str | None) -> tuple[int, int]:
    db = SessionLocal()
    u = User(pseudonymous_token=os.urandom(32).hex(), reliability_index=ri, age_tier="Adult")
    db.add(u)
    db.flush()
    r = Report(
        user_id=u.id,
        text="x" * 20,
        tier=1,
        embedding=[0.0],
        verification_status=verdict,
        ri_applied=False,
    )
    db.add(r)
    db.commit()
    uid, rid = u.id, r.id
    db.close()
    return uid, rid


def test_verified_adds_50_capped_at_1000():
    uid, _ = _seed(980, "Verified")
    db = SessionLocal()
    changes = recalculate_pending(db)
    assert len(changes) == 1
    assert changes[0].ri_after == RI_MAX
    assert changes[0].delta == 20
    db.close()


def test_malicious_subtracts_150_floored_at_0():
    uid, _ = _seed(100, "Malicious")
    db = SessionLocal()
    changes = recalculate_pending(db)
    assert len(changes) == 1
    assert changes[0].ri_after == RI_MIN
    assert changes[0].delta == -100
    db.close()


def test_idempotent_second_run_is_noop():
    _seed(500, "Verified")
    db = SessionLocal()
    first = recalculate_pending(db)
    second = recalculate_pending(db)
    assert len(first) == 1
    assert second == []
    db.close()


def test_ri_adjusted_audit_entry_written():
    _seed(500, "Malicious")
    db = SessionLocal()
    recalculate_pending(db)
    entries = db.query(AuditLedger).filter(AuditLedger.event_type == "RI_ADJUSTED").all()
    assert any(e.details and e.details.get("verdict") == "Malicious" for e in entries)
    db.close()


def test_unverified_report_skipped():
    _seed(500, None)
    db = SessionLocal()
    changes = recalculate_pending(db)
    assert changes == []
    db.close()
