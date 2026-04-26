import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database

# StaticPool + check_same_thread=False lets the in-memory SQLite be
# shared across the TestClient's worker thread and the test's main thread.
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
from app.models.audit_ledger import AuditLedger  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.user import User  # noqa: E402

SessionLocal = test_session_factory
from app.services.recovery import (  # noqa: E402
    MNEMONIC_WORD_COUNT,
    generate_mnemonic,
    hash_mnemonic,
    is_valid_mnemonic,
    verify_mnemonic,
)


def setup_module(module):
    # Rebind here, not at import, so this module's engine wins regardless of
    # which other test files were imported earlier in the run.
    database.engine = test_engine
    database.SessionLocal = test_session_factory
    Base.metadata.create_all(bind=test_engine)


def setup_function(function):
    db = SessionLocal()
    db.query(SessionModel).delete()
    db.query(AuditLedger).delete()
    db.query(User).delete()
    db.commit()
    db.close()


# ---- service-level tests ----


def test_generate_yields_24_valid_words():
    m = generate_mnemonic()
    words = m.split()
    assert len(words) == MNEMONIC_WORD_COUNT
    assert is_valid_mnemonic(m)


def test_hash_is_deterministic_and_normalizes_whitespace_and_case():
    m = generate_mnemonic()
    h1 = hash_mnemonic(m)
    h2 = hash_mnemonic(m.upper())
    h3 = hash_mnemonic("   " + m.replace(" ", "  ") + "\n")
    assert h1 == h2 == h3
    assert len(h1) == 64


def test_hash_changes_when_a_word_changes():
    words = generate_mnemonic().split()
    other = " ".join(["abandon"] + words[1:])  # almost certainly different first word
    if other.split()[0] == words[0]:
        other = " ".join(["ability"] + words[1:])
    assert hash_mnemonic(" ".join(words)) != hash_mnemonic(other)


def test_verify_rejects_none_and_garbage():
    m = generate_mnemonic()
    h = hash_mnemonic(m)
    assert verify_mnemonic(m, h) is True
    assert verify_mnemonic(m, None) is False
    assert verify_mnemonic("totally bogus phrase here", h) is False


def test_invalid_bip39_checksum_caught():
    # 24 random non-wordlist tokens
    junk = " ".join(["zzz"] * 24)
    assert is_valid_mnemonic(junk) is False


# ---- endpoint-level tests ----


def test_register_returns_mnemonic_only_once():
    with TestClient(app) as c:
        r1 = c.post("/auth/register", json={"national_id": "RECOVER-1"}).json()
        assert r1["created"] is True
        assert r1["recovery_mnemonic"] is not None
        assert len(r1["recovery_mnemonic"].split()) == 24

        r2 = c.post("/auth/register", json={"national_id": "RECOVER-1"}).json()
        assert r2["created"] is False
        assert r2["recovery_mnemonic"] is None
        assert r2["pseudonymous_token"] == r1["pseudonymous_token"]


def test_recover_succeeds_with_correct_mnemonic_and_id():
    with TestClient(app) as c:
        reg = c.post("/auth/register", json={"national_id": "RECOVER-2"}).json()
        pt = reg["pseudonymous_token"]
        mnemonic = reg["recovery_mnemonic"]

        r = c.post("/auth/recover", json={"national_id": "RECOVER-2", "mnemonic": mnemonic})
        assert r.status_code == 200
        body = r.json()
        assert body["pseudonymous_token"] == pt
        assert len(body["session_token"]) >= 32
        assert "expires_at" in body

        # Session row exists in DB
        db = SessionLocal()
        sess = db.query(SessionModel).filter(SessionModel.session_token == body["session_token"]).one()
        assert sess.pseudonymous_token == pt
        db.close()


def test_recover_fails_on_wrong_mnemonic():
    with TestClient(app) as c:
        c.post("/auth/register", json={"national_id": "RECOVER-3"}).json()
        bogus = generate_mnemonic()
        r = c.post("/auth/recover", json={"national_id": "RECOVER-3", "mnemonic": bogus})
        assert r.status_code == 401
        assert r.json()["detail"] == "Recovery failed."


def test_recover_fails_on_unknown_national_id_with_same_generic_message():
    with TestClient(app) as c:
        # Never registered
        r = c.post("/auth/recover", json={"national_id": "NEVER-EXISTED", "mnemonic": generate_mnemonic()})
        assert r.status_code == 401
        # Identical wording to wrong-mnemonic case — no oracle on registration.
        assert r.json()["detail"] == "Recovery failed."


def test_recover_fails_on_garbage_mnemonic():
    with TestClient(app) as c:
        c.post("/auth/register", json={"national_id": "RECOVER-4"}).json()
        r = c.post("/auth/recover", json={"national_id": "RECOVER-4", "mnemonic": "not even close"})
        assert r.status_code == 401


def test_failed_recovery_attempts_audit_logged():
    with TestClient(app) as c:
        c.post("/auth/register", json={"national_id": "RECOVER-5"}).json()
        c.post("/auth/recover", json={"national_id": "RECOVER-5", "mnemonic": generate_mnemonic()})
        c.post("/auth/recover", json={"national_id": "RECOVER-5", "mnemonic": generate_mnemonic()})

    db = SessionLocal()
    failures = db.query(AuditLedger).filter(AuditLedger.event_type == "AUTH_RECOVERY_FAILED").all()
    db.close()
    assert len(failures) == 2


def test_successful_recovery_audit_logged():
    with TestClient(app) as c:
        reg = c.post("/auth/register", json={"national_id": "RECOVER-6"}).json()
        c.post("/auth/recover", json={"national_id": "RECOVER-6", "mnemonic": reg["recovery_mnemonic"]})

    db = SessionLocal()
    successes = db.query(AuditLedger).filter(AuditLedger.event_type == "AUTH_RECOVERY_SUCCESS").all()
    db.close()
    assert len(successes) == 1


def test_recovery_hash_is_persisted_not_mnemonic():
    with TestClient(app) as c:
        reg = c.post("/auth/register", json={"national_id": "RECOVER-7"}).json()
        mnemonic = reg["recovery_mnemonic"]
        pt = reg["pseudonymous_token"]

    db = SessionLocal()
    user = db.query(User).filter(User.pseudonymous_token == pt).one()
    assert user.recovery_hash is not None
    assert len(user.recovery_hash) == 64
    # Plaintext mnemonic must not be stored anywhere on the user row
    for word in mnemonic.split():
        assert word not in (user.recovery_hash or "")
    db.close()
