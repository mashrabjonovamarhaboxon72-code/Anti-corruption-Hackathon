"""Integration test: the rate-limit decorator on /auth/recover actually
fires through the FastAPI route, returns 429, and includes Retry-After."""

import os
import sys
from pathlib import Path

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
from app.models.user import User  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402

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
    auth_router.recover_limiter.reset()  # clean slate per test


def test_six_attempts_in_window_yields_429_on_the_sixth():
    with TestClient(app) as c:
        # Create one valid user so 5 of the attempts could realistically succeed
        c.post("/auth/register", json={"national_id": "RL-1"})

        bogus = {"national_id": "RL-1", "mnemonic": "abandon " * 23 + "abandon"}

        for i in range(5):
            r = c.post("/auth/recover", json=bogus)
            assert r.status_code == 401, f"attempt {i+1} should be 401 (failed recovery), got {r.status_code}"

        # 6th attempt within the window
        r = c.post("/auth/recover", json=bogus)
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) >= 1
        assert "Too many attempts" in r.json()["detail"]


def test_successful_attempts_count_toward_quota():
    """An attacker who phishes one valid mnemonic shouldn't get unlimited
    other recoveries from the same IP — every attempt counts."""
    with TestClient(app) as c:
        reg = c.post("/auth/register", json={"national_id": "RL-2"}).json()
        good = {"national_id": "RL-2", "mnemonic": reg["recovery_mnemonic"]}

        for i in range(5):
            r = c.post("/auth/recover", json=good)
            assert r.status_code == 200, f"attempt {i+1} should succeed"

        r = c.post("/auth/recover", json=good)
        assert r.status_code == 429


def test_429_response_does_not_consume_quota():
    """While blocked, an attacker keeps polling. Each blocked poll must NOT
    push the unlock time further out — otherwise we lock out forever."""
    with TestClient(app) as c:
        c.post("/auth/register", json={"national_id": "RL-3"})
        bogus = {"national_id": "RL-3", "mnemonic": "abandon " * 23 + "abandon"}
        for _ in range(5):
            c.post("/auth/recover", json=bogus)

        # First blocked response captures retry_after
        r1 = c.post("/auth/recover", json=bogus)
        assert r1.status_code == 429
        retry1 = int(r1.headers["Retry-After"])

        # Polling more times shouldn't increase retry_after
        for _ in range(10):
            r = c.post("/auth/recover", json=bogus)
            assert r.status_code == 429
            assert int(r.headers["Retry-After"]) <= retry1


def test_other_endpoints_unaffected_by_recover_limit():
    """The limiter is per-route. Hitting /auth/recover until 429 must not
    block /auth/register or anything else on the same IP."""
    with TestClient(app) as c:
        c.post("/auth/register", json={"national_id": "RL-4"})
        bogus = {"national_id": "RL-4", "mnemonic": "abandon " * 23 + "abandon"}
        for _ in range(6):
            c.post("/auth/recover", json=bogus)
        # /auth/register still works on the same IP
        r = c.post("/auth/register", json={"national_id": "RL-5"})
        assert r.status_code in (200, 201)
