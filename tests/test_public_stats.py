import os
import sys
import time
from datetime import datetime, timedelta
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
from app.services.public_stats import (  # noqa: E402
    TIER_FISCAL_IMPACT_UZS,
    StatsCache,
    compute_stats,
)


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def setup_function(function):
    db = SessionLocal()
    db.query(Report).delete()
    db.query(User).delete()
    db.commit()
    db.close()


def _user() -> int:
    db = SessionLocal()
    u = User(pseudonymous_token=os.urandom(32).hex(), age_tier="Adult")
    db.add(u); db.commit(); db.refresh(u); uid = u.id; db.close()
    return uid


def _report(uid: int, *, tier: int, verdict: str | None, dept: str | None = None, created_at: datetime | None = None) -> int:
    db = SessionLocal()
    r = Report(
        user_id=uid,
        text="x" * 20,
        tier=tier,
        embedding=[0.0],
        verification_status=verdict,
        target_department_id=dept,
    )
    if created_at:
        r.created_at = created_at
    db.add(r); db.commit(); db.refresh(r); rid = r.id; db.close()
    return rid


def test_total_verified_count():
    u = _user()
    _report(u, tier=1, verdict="Verified", dept="DEPT-TAX")
    _report(u, tier=2, verdict="Verified", dept="DEPT-TAX")
    _report(u, tier=3, verdict=None, dept="DEPT-TAX")  # not verified
    _report(u, tier=4, verdict="Malicious", dept="DEPT-TAX")  # not verified
    db = SessionLocal()
    s = compute_stats(db); db.close()
    assert s.total_verified_reports == 2


def test_civic_impact_sums_tiers_of_verified_only():
    u = _user()
    _report(u, tier=4, verdict="Verified")  # +4
    _report(u, tier=3, verdict="Verified")  # +3
    _report(u, tier=4, verdict="Malicious")  # ignored
    _report(u, tier=2, verdict=None)         # ignored
    db = SessionLocal()
    s = compute_stats(db); db.close()
    assert s.total_civic_impact == 7


def test_department_breakdown_groups_and_orders():
    u = _user()
    for _ in range(3):
        _report(u, tier=1, verdict="Verified", dept="DEPT-TAX")
    for _ in range(5):
        _report(u, tier=1, verdict="Verified", dept="DEPT-CUSTOMS")
    _report(u, tier=1, verdict="Verified", dept=None)  # UNSPECIFIED
    db = SessionLocal()
    s = compute_stats(db); db.close()

    counts = {b.department_id: b.verified_report_count for b in s.reports_by_department}
    assert counts == {"DEPT-CUSTOMS": 5, "DEPT-TAX": 3, "UNSPECIFIED": 1}
    # Ordered by count desc
    assert s.reports_by_department[0].department_id == "DEPT-CUSTOMS"


def test_recent_badges_omits_user_ids_and_uses_4th_report_timestamp():
    fast = _user()
    base = datetime(2026, 1, 1, 10, 0, 0)
    timestamps = [base + timedelta(hours=i) for i in range(5)]
    for t in timestamps:
        _report(fast, tier=3, verdict="Verified", created_at=t)

    slow = _user()
    for _ in range(3):  # only 3 verified -> no badge yet
        _report(slow, tier=4, verdict="Verified")

    db = SessionLocal()
    s = compute_stats(db); db.close()

    assert len(s.recent_corruption_fighter_badges) == 1
    badge = s.recent_corruption_fighter_badges[0]
    assert badge.badge_id == "BADGE-CORRUPTION-FIGHTER"
    # Earned at timestamp of the 4th verified Tier-3+ report (index 3)
    assert badge.earned_at.startswith(timestamps[3].isoformat())

    # No fields revealing user identity
    raw = badge.__dict__
    for forbidden in ("user_id", "pseudonymous_token", "id", "uid"):
        assert forbidden not in raw, f"badge leaked {forbidden}"


def test_no_pii_in_full_stats_payload():
    u = _user()
    for _ in range(4):
        _report(u, tier=4, verdict="Verified", dept="DEPT-TAX")

    db = SessionLocal()
    payload = compute_stats(db).to_dict(); db.close()

    flat = repr(payload)
    # Sanity: no obvious PII leakage routes.
    assert "pseudonymous_token" not in flat
    assert "user_id" not in flat
    assert "national_id" not in flat


def test_cache_returns_same_object_within_ttl():
    cache = StatsCache(ttl_seconds=60)
    db = SessionLocal()
    a = cache.get(db)
    b = cache.get(db)
    db.close()
    assert a is b  # identical object reference proves no recomputation


def test_cache_recomputes_after_expiry():
    cache = StatsCache(ttl_seconds=0)  # immediate expiry
    db = SessionLocal()
    a = cache.get(db)
    time.sleep(0.01)
    b = cache.get(db)
    db.close()
    assert a is not b  # forced recompute → fresh object


def test_cache_invalidate_forces_recompute():
    cache = StatsCache(ttl_seconds=3600)
    db = SessionLocal()
    a = cache.get(db)
    cache.invalidate()
    b = cache.get(db)
    db.close()
    assert a is not b


# ---- civic_roi_summary ----


def test_civic_roi_zero_state_emits_all_four_tiers():
    """An empty system should still expose every tier row so the dashboard
    can render a complete table on day one."""
    db = SessionLocal()
    s = compute_stats(db); db.close()

    roi = s.civic_roi_summary
    assert roi.currency == "UZS"
    assert roi.total_estimated_funds_protected == 0
    assert [t.tier for t in roi.by_tier] == [1, 2, 3, 4]
    for t in roi.by_tier:
        assert t.verified_report_count == 0
        assert t.subtotal_uzs == 0


def test_civic_roi_sums_per_tier_and_only_counts_verified():
    u = _user()
    # Verified contributors
    _report(u, tier=4, verdict="Verified")  # +100M
    _report(u, tier=4, verdict="Verified")  # +100M
    _report(u, tier=3, verdict="Verified")  # + 50M
    _report(u, tier=1, verdict="Verified")  # +  2M
    # Should NOT be counted
    _report(u, tier=4, verdict="Malicious")
    _report(u, tier=3, verdict=None)
    _report(u, tier=2, verdict="Malicious")

    db = SessionLocal()
    s = compute_stats(db); db.close()
    roi = s.civic_roi_summary

    assert roi.total_estimated_funds_protected == 252_000_000
    by_tier = {t.tier: t for t in roi.by_tier}
    assert by_tier[4].verified_report_count == 2
    assert by_tier[4].subtotal_uzs == 200_000_000
    assert by_tier[3].verified_report_count == 1
    assert by_tier[3].subtotal_uzs == 50_000_000
    assert by_tier[2].verified_report_count == 0
    assert by_tier[2].subtotal_uzs == 0
    assert by_tier[1].verified_report_count == 1
    assert by_tier[1].subtotal_uzs == 2_000_000


def test_civic_roi_table_matches_constants():
    """The conversion table is echoed in the response so the frontend can
    show users how subtotals were derived. It must equal the constants."""
    db = SessionLocal()
    s = compute_stats(db); db.close()
    assert s.civic_roi_summary.tier_impact_table == TIER_FISCAL_IMPACT_UZS


def test_tier_4_estimated_at_least_100m():
    """The user-facing claim is 'Tier 4 = 100,000,000+ UZS'; if anyone
    tunes this constant down, the assertion catches it before the demo."""
    assert TIER_FISCAL_IMPACT_UZS[4] >= 100_000_000


def test_civic_roi_serializes_in_payload():
    u = _user()
    _report(u, tier=4, verdict="Verified")
    db = SessionLocal()
    payload = compute_stats(db).to_dict(); db.close()

    assert "civic_roi_summary" in payload
    roi = payload["civic_roi_summary"]
    assert roi["currency"] == "UZS"
    assert roi["total_estimated_funds_protected"] == 100_000_000
    assert isinstance(roi["by_tier"], list) and len(roi["by_tier"]) == 4
    # No PII smuggled in via the new section
    flat = repr(roi)
    for forbidden in ("pseudonymous_token", "user_id", "national_id"):
        assert forbidden not in flat
