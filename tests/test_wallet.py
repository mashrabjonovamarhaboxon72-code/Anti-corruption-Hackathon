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

test_engine = create_engine("sqlite:///:memory:", future=True)
database.engine = test_engine
database.SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

from app.database import Base, SessionLocal  # noqa: E402
from app.models.audit_ledger import AuditLedger  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.voucher import Voucher  # noqa: E402
from app.services.benefits_catalog import find_benefit  # noqa: E402
from app.services.wallet import generate_voucher_code, issue_voucher, self_destruct_transaction  # noqa: E402


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _make_user(tier: str, points: int) -> User:
    db = SessionLocal()
    u = User(
        pseudonymous_token=os.urandom(32).hex(),
        reliability_index=500,
        points_total=points,
        age_tier=tier,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    db.close()
    return u


def test_voucher_codes_are_unguessable_and_unique():
    codes = {generate_voucher_code() for _ in range(50)}
    assert len(codes) == 50
    for c in codes:
        assert c.startswith("V-") and len(c) >= 14


def test_self_destruct_severs_pt_link():
    user = _make_user("Adult", 1000)
    benefit = find_benefit("BEN-TAX-REBATE-100")

    db = SessionLocal()
    voucher = issue_voucher(db, pseudonymous_token=user.pseudonymous_token, benefit=benefit)
    assert voucher.redeemer_pt == user.pseudonymous_token

    voucher.status = "Used"
    from datetime import datetime as _dt

    voucher.used_at = _dt.utcnow()
    db.commit()
    db.refresh(voucher)

    voucher = self_destruct_transaction(db, voucher)
    assert voucher.redeemer_pt is None
    assert voucher.self_destructed_at is not None

    ledger_entries = db.query(AuditLedger).filter(AuditLedger.event_type == "VOUCHER_USED").all()
    assert len(ledger_entries) >= 1
    last = ledger_entries[-1]
    # Audit row must NOT contain the full PT — only a non-reversible prefix.
    assert user.pseudonymous_token not in (last.details or {}).values()
    db.close()


def test_self_destruct_refuses_unused_voucher():
    user = _make_user("Senior", 1000)
    benefit = find_benefit("BEN-HEALTH-VOUCHER")
    db = SessionLocal()
    voucher = issue_voucher(db, pseudonymous_token=user.pseudonymous_token, benefit=benefit)
    with pytest.raises(ValueError):
        self_destruct_transaction(db, voucher)
    db.close()
