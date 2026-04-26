"""Aggregated, non-identifiable public dashboard data.

The shape returned here is deliberately minimal: counts, sums, and
department codes — never a user_id, never a pseudonymous_token. The
`recent_corruption_fighter_badges` list is the only place where
"someone" is mentioned, and even there we only emit the timestamp at
which they qualified, not who they are.

Caching: results are wrapped in a TTL-bounded `StatsCache`. The first
request after expiry recomputes; subsequent requests within the window
return the same dict by identity. This is the in-process equivalent of
a Postgres MATERIALIZED VIEW with a refresh interval — same access
pattern, no infrastructure. Swap to a real materialized view if the
node count or query cost grows.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import Lock

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import PUBLIC_STATS_RECENT_BADGES_LIMIT, PUBLIC_STATS_TTL_SECONDS
from app.models.report import Report
from app.services.badges import (
    CORRUPTION_FIGHTER_BADGE,
    CORRUPTION_FIGHTER_MIN_TIER,
    CORRUPTION_FIGHTER_MIN_VERIFIED,
)


# Estimated fiscal impact per Verified report tier, in Uzbekistani so'm (UZS).
# These are *order-of-magnitude* estimates derived from public corruption-case
# reporting; they're shown in the dashboard as "Estimated Public Funds
# Protected" and should be treated as illustrative, not auditable. Tune the
# constants here, not in the consumer — the dashboard, the demo seed, and any
# downstream report all read from this single source of truth.
TIER_FISCAL_IMPACT_UZS: dict[int, int] = {
    1: 2_000_000,        # petty bribe at a window/desk
    2: 15_000_000,       # mid-level extortion or fee fabrication
    3: 50_000_000,       # contract-skimming, admissions fraud, etc.
    4: 100_000_000,      # high-impact: senior official, organized scheme
}
FISCAL_CURRENCY = "UZS"


@dataclass
class DepartmentBreakdown:
    department_id: str
    verified_report_count: int


@dataclass
class RecentBadge:
    badge_id: str
    name: str
    earned_at: str  # ISO timestamp; user identifiers omitted by design


@dataclass
class TierImpact:
    tier: int
    verified_report_count: int
    impact_per_report_uzs: int
    subtotal_uzs: int


@dataclass
class CivicRoiSummary:
    """Aggregate fiscal-impact estimate for the public dashboard.

    Counts Verified reports only — accusations that haven't passed an
    auditor's verdict don't claim "funds protected" status.
    """

    currency: str
    total_estimated_funds_protected: int
    by_tier: list[TierImpact]
    tier_impact_table: dict[int, int]  # echoed so the frontend can show the conversion table


@dataclass
class PublicStats:
    total_verified_reports: int
    reports_by_department: list[DepartmentBreakdown]
    total_civic_impact: int
    civic_roi_summary: CivicRoiSummary
    recent_corruption_fighter_badges: list[RecentBadge]
    generated_at: str
    cache_ttl_seconds: int = field(default=PUBLIC_STATS_TTL_SECONDS)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _verified_count(db: Session) -> int:
    return (
        db.query(func.count(Report.id))
        .filter(Report.verification_status == "Verified")
        .scalar()
        or 0
    )


def _civic_impact(db: Session) -> int:
    return (
        db.query(func.coalesce(func.sum(Report.tier), 0))
        .filter(Report.verification_status == "Verified")
        .scalar()
        or 0
    )


def _civic_roi(db: Session) -> CivicRoiSummary:
    """Group Verified reports by tier, multiply by the tier's fiscal-impact
    estimate, sum into a grand total. Tiers with zero verified reports are
    still emitted in `by_tier` so the dashboard can show all four rows even
    on a quiet day — better UX than a row appearing/disappearing."""
    rows = (
        db.query(Report.tier, func.count(Report.id))
        .filter(Report.verification_status == "Verified")
        .group_by(Report.tier)
        .all()
    )
    counts_by_tier: dict[int, int] = {tier: 0 for tier in TIER_FISCAL_IMPACT_UZS}
    for tier, count in rows:
        if tier in counts_by_tier:
            counts_by_tier[tier] = count

    by_tier: list[TierImpact] = []
    grand_total = 0
    for tier in sorted(TIER_FISCAL_IMPACT_UZS):
        impact = TIER_FISCAL_IMPACT_UZS[tier]
        count = counts_by_tier[tier]
        subtotal = impact * count
        grand_total += subtotal
        by_tier.append(
            TierImpact(
                tier=tier,
                verified_report_count=count,
                impact_per_report_uzs=impact,
                subtotal_uzs=subtotal,
            )
        )

    return CivicRoiSummary(
        currency=FISCAL_CURRENCY,
        total_estimated_funds_protected=grand_total,
        by_tier=by_tier,
        tier_impact_table=dict(TIER_FISCAL_IMPACT_UZS),
    )


def _by_department(db: Session) -> list[DepartmentBreakdown]:
    rows = (
        db.query(Report.target_department_id, func.count(Report.id))
        .filter(Report.verification_status == "Verified")
        .group_by(Report.target_department_id)
        .order_by(func.count(Report.id).desc())
        .all()
    )
    return [
        DepartmentBreakdown(
            department_id=dept or "UNSPECIFIED",
            verified_report_count=count,
        )
        for dept, count in rows
    ]


def _recent_badges(db: Session, limit: int) -> list[RecentBadge]:
    """Find users whose Verified Tier-3+ report count crossed the badge
    threshold, and emit the timestamp at which they crossed it.

    We deliberately do not return the user_id. The dashboard is meant to
    say "someone earned this badge today", not "user #123 did".
    """
    rows = (
        db.query(Report.user_id, Report.created_at)
        .filter(Report.verification_status == "Verified")
        .filter(Report.tier >= CORRUPTION_FIGHTER_MIN_TIER)
        .order_by(Report.user_id, Report.created_at)
        .all()
    )

    per_user: dict[int, list[datetime]] = defaultdict(list)
    for uid, created in rows:
        per_user[uid].append(created)

    earned_at_per_user: list[datetime] = []
    for uid, timestamps in per_user.items():
        if len(timestamps) >= CORRUPTION_FIGHTER_MIN_VERIFIED:
            earned_at_per_user.append(timestamps[CORRUPTION_FIGHTER_MIN_VERIFIED - 1])

    earned_at_per_user.sort(reverse=True)

    return [
        RecentBadge(
            badge_id=CORRUPTION_FIGHTER_BADGE["id"],
            name=CORRUPTION_FIGHTER_BADGE["name"],
            earned_at=ts.isoformat() + "Z",
        )
        for ts in earned_at_per_user[:limit]
    ]


def compute_stats(db: Session, *, recent_limit: int = PUBLIC_STATS_RECENT_BADGES_LIMIT) -> PublicStats:
    return PublicStats(
        total_verified_reports=_verified_count(db),
        reports_by_department=_by_department(db),
        total_civic_impact=int(_civic_impact(db)),
        civic_roi_summary=_civic_roi(db),
        recent_corruption_fighter_badges=_recent_badges(db, limit=recent_limit),
        generated_at=datetime.utcnow().isoformat() + "Z",
        cache_ttl_seconds=PUBLIC_STATS_TTL_SECONDS,
    )


class StatsCache:
    """In-process TTL cache. Single global instance is fine — FastAPI
    runs the request handler in a threadpool, so we guard recomputation
    with a Lock to avoid thundering-herd recomputes."""

    def __init__(self, ttl_seconds: int = PUBLIC_STATS_TTL_SECONDS):
        self._ttl = max(0, ttl_seconds)
        self._value: PublicStats | None = None
        self._expires_at: float = 0.0
        self._lock = Lock()

    def get(self, db: Session) -> PublicStats:
        now = time.monotonic()
        if self._value is not None and now < self._expires_at:
            return self._value
        with self._lock:
            now = time.monotonic()
            if self._value is None or now >= self._expires_at:
                self._value = compute_stats(db)
                self._expires_at = now + self._ttl
            return self._value

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0


_cache = StatsCache()


def get_cache() -> StatsCache:
    return _cache
