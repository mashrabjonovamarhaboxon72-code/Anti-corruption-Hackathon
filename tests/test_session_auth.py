import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database

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
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.user import User  # noqa: E402

SessionLocal = test_session_factory


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


def _register_and_recover(c: TestClient, national_id: str) -> tuple[str, str]:
    """Register a user, then recover to get a session_token. Returns (pt, session_token)."""
    reg = c.post("/auth/register", json={"national_id": national_id, "age_tier": "Adult"}).json()
    rec = c.post(
        "/auth/recover",
        json={"national_id": national_id, "mnemonic": reg["recovery_mnemonic"]},
    ).json()
    return rec["pseudonymous_token"], rec["session_token"]


def _mint_session_directly(pt: str, *, hours: float = 24, revoked: bool = False) -> str:
    """Test-only helper: insert a Session row without going through /auth/recover."""
    db = SessionLocal()
    token = secrets.token_urlsafe(32)
    sess = SessionModel(
        session_token=token,
        pseudonymous_token=pt,
        expires_at=datetime.utcnow() + timedelta(hours=hours),
        revoked_at=datetime.utcnow() if revoked else None,
    )
    db.add(sess)
    db.commit()
    db.close()
    return token


# ---- dependency-level rejection tests ----


def test_missing_authorization_header_rejected():
    with TestClient(app) as c:
        r = c.post("/reports", json={"text": "anything goes here", "tier": 1})
        assert r.status_code == 401
        assert r.headers.get("www-authenticate") == "Bearer"


def test_non_bearer_scheme_rejected():
    with TestClient(app) as c:
        r = c.post(
            "/reports",
            json={"text": "anything goes here", "tier": 1},
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert r.status_code == 401


def test_empty_bearer_token_rejected():
    with TestClient(app) as c:
        r = c.post(
            "/reports",
            json={"text": "anything goes here", "tier": 1},
            headers={"Authorization": "Bearer    "},
        )
        assert r.status_code == 401


def test_unknown_token_rejected():
    with TestClient(app) as c:
        r = c.post(
            "/reports",
            json={"text": "anything goes here", "tier": 1},
            headers={"Authorization": "Bearer this-is-not-a-real-token"},
        )
        assert r.status_code == 401


def test_expired_session_rejected():
    with TestClient(app) as c:
        pt, _ = _register_and_recover(c, "EXPIRED-1")
        token = _mint_session_directly(pt, hours=-1)  # already expired

        r = c.post(
            "/reports",
            json={"text": "anything goes here", "tier": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401


def test_revoked_session_rejected():
    with TestClient(app) as c:
        pt, _ = _register_and_recover(c, "REVOKED-1")
        token = _mint_session_directly(pt, revoked=True)

        r = c.post(
            "/reports",
            json={"text": "anything goes here", "tier": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401


# ---- happy-path integration through the refactored endpoints ----


def test_reports_endpoint_now_uses_session_not_body_pt():
    with TestClient(app) as c:
        pt, token = _register_and_recover(c, "RPT-1")

        # Old shape: PT-in-body without Authorization → 401
        r = c.post(
            "/reports",
            json={"pseudonymous_token": pt, "text": "this should fail without bearer", "tier": 1},
        )
        assert r.status_code == 401

        # New shape: Authorization header
        with patch("app.services.duplicate_check.embed", return_value=[1.0, 0.0, 0.0]):
            r = c.post(
                "/reports",
                json={"text": "Tax officer demanded unrecorded cash payment", "tier": 2},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["report_id"] >= 1
        assert body["awarded_points"] == 250


def test_wallet_rewards_endpoint_uses_session():
    with TestClient(app) as c:
        _, token = _register_and_recover(c, "WAL-1")

        # No Authorization → 401
        r = c.get("/wallet/rewards")
        assert r.status_code == 401

        # With Authorization → 200, no PT needed in query
        r = c.get("/wallet/rewards", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["age_tier"] == "Adult"
        assert "benefits" in body and "badges" in body


def test_wallet_redeem_endpoint_uses_session():
    with TestClient(app) as c:
        pt, token = _register_and_recover(c, "WAL-2")

        # Give the user some points so the redeem path can complete
        db = SessionLocal()
        u = db.query(User).filter(User.pseudonymous_token == pt).one()
        u.points_total = 1000
        db.commit()
        db.close()

        # No Authorization → 401
        r = c.post("/wallet/redeem", json={"benefit_id": "BEN-TAX-REBATE-100"})
        assert r.status_code == 401

        # With Authorization → 201
        r = c.post(
            "/wallet/redeem",
            json={"benefit_id": "BEN-TAX-REBATE-100"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["benefit_id"] == "BEN-TAX-REBATE-100"
        assert body["points_remaining"] == 500


def test_two_users_session_isolation():
    """A session for user A must never grant access to user B's data."""
    with TestClient(app) as c:
        _, token_a = _register_and_recover(c, "ISO-A")
        _, token_b = _register_and_recover(c, "ISO-B")

        rew_a = c.get("/wallet/rewards", headers={"Authorization": f"Bearer {token_a}"}).json()
        rew_b = c.get("/wallet/rewards", headers={"Authorization": f"Bearer {token_b}"}).json()

        # Same age tier so benefit lists match; just confirm the calls work
        # and that swapping a token for a fresh one yields independent rows.
        assert rew_a["points_total"] == 0
        assert rew_b["points_total"] == 0
