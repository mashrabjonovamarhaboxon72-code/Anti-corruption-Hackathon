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
from app.models.audit_ledger import AuditLedger  # noqa: E402
from app.models.protection_order import ProtectionOrder  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.protection_order import (  # noqa: E402
    PROTECTION_RI_THRESHOLD,
    maybe_issue,
    sign_payload,
    verify_signature,
)


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _seed(*, ri: int, tier: int) -> tuple[int, int]:
    db = SessionLocal()
    u = User(pseudonymous_token=os.urandom(32).hex(), reliability_index=ri, age_tier="Adult")
    db.add(u)
    db.flush()
    r = Report(user_id=u.id, text="x" * 20, tier=tier, embedding=[0.0])
    db.add(r)
    db.commit()
    uid, rid = u.id, r.id
    db.close()
    return uid, rid


def test_signature_round_trips():
    payload = {"order_id": "DPO-X", "tier": 4, "report_id": 1}
    sig = sign_payload(payload)
    assert verify_signature(payload, sig) is True

    tampered = dict(payload, tier=1)
    assert verify_signature(tampered, sig) is False


def test_signature_is_canonical_key_order_invariant():
    a = {"a": 1, "b": 2, "c": 3}
    b = {"c": 3, "b": 2, "a": 1}
    assert sign_payload(a) == sign_payload(b)


def test_issued_for_tier4_high_ri_verified():
    uid, rid = _seed(ri=950, tier=4)
    db = SessionLocal()
    user = db.get(User, uid)
    report = db.get(Report, rid)
    pt = user.pseudonymous_token
    issued = maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Verified")
    db.close()

    assert issued is not None
    assert issued.payload["tier"] == 4
    assert issued.payload["pseudonymous_token"] == pt
    assert issued.payload["ri_at_issue"] == 950
    assert verify_signature(issued.payload, issued.signature) is True


def test_not_issued_for_tier3():
    uid, rid = _seed(ri=950, tier=3)
    db = SessionLocal()
    user = db.get(User, uid); report = db.get(Report, rid)
    assert maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Verified") is None
    db.close()


def test_not_issued_when_ri_at_or_below_threshold():
    uid, rid = _seed(ri=PROTECTION_RI_THRESHOLD, tier=4)
    db = SessionLocal()
    user = db.get(User, uid); report = db.get(Report, rid)
    assert maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Verified") is None
    db.close()


def test_not_issued_when_malicious():
    uid, rid = _seed(ri=950, tier=4)
    db = SessionLocal()
    user = db.get(User, uid); report = db.get(Report, rid)
    assert maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Malicious") is None
    db.close()


def test_idempotent_no_duplicate_for_same_report():
    uid, rid = _seed(ri=950, tier=4)
    db = SessionLocal()
    user = db.get(User, uid); report = db.get(Report, rid)
    first = maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Verified")
    second = maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Verified")
    db.close()

    assert first is not None and second is not None
    assert first.order_id == second.order_id
    db = SessionLocal()
    rows = db.query(ProtectionOrder).filter(ProtectionOrder.report_id == rid).all()
    db.close()
    assert len(rows) == 1


def test_audit_ledger_logs_issuance():
    uid, rid = _seed(ri=950, tier=4)
    db = SessionLocal()
    user = db.get(User, uid); report = db.get(Report, rid)
    maybe_issue(db, user=user, report=report, auditor_id="AUD-002", verdict="Verified")
    entries = db.query(AuditLedger).filter(AuditLedger.event_type == "PROTECTION_ORDER_ISSUED").all()
    db.close()
    assert any(e.report_id == rid and e.details and "order_id" in e.details for e in entries)
