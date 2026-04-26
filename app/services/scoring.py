from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import RI_BASELINE
from app.models.audit_ledger import AuditLedger
from app.models.user import User

CORRUPTION_TIERS: dict[int, int] = {
    1: 100,
    2: 250,
    3: 500,
    4: 1000,
}


@dataclass
class PointAward:
    user_id: int
    report_id: int
    tier: int
    base_points: int
    ri_at_award: int
    ri_multiplier: float
    awarded_points: int


def _ri_multiplier(reliability_index: int) -> float:
    """Reliability Index 0-1000 maps linearly to 0.0x-2.0x, centered at 1.0x
    when RI == 500 (the baseline new-user value)."""
    clamped = max(0, min(1000, reliability_index))
    return clamped / RI_BASELINE


def award_points(
    db: Session,
    *,
    user: User,
    report_id: int,
    tier: int,
) -> PointAward:
    if tier not in CORRUPTION_TIERS:
        raise ValueError(f"Unknown corruption tier {tier!r}. Must be one of {sorted(CORRUPTION_TIERS)}.")

    base = CORRUPTION_TIERS[tier]
    multiplier = _ri_multiplier(user.reliability_index)
    awarded = int(round(base * multiplier))

    user.points_total = (user.points_total or 0) + awarded

    ledger_entry = AuditLedger(
        user_id=user.id,
        report_id=report_id,
        tier=tier,
        base_points=base,
        ri_at_award=user.reliability_index,
        ri_multiplier=multiplier,
        awarded_points=awarded,
        event_type="POINTS_AWARDED",
    )
    db.add(ledger_entry)
    db.commit()

    return PointAward(
        user_id=user.id,
        report_id=report_id,
        tier=tier,
        base_points=base,
        ri_at_award=user.reliability_index,
        ri_multiplier=multiplier,
        awarded_points=awarded,
    )
