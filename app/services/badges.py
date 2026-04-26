"""Achievement badges shown in /wallet/rewards.

Badges are derived signals — they read state, never mutate it. So a
re-computation always yields the canonical answer for the current DB
state. No badge "table" is necessary.
"""

from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.user import User

CORRUPTION_FIGHTER_BADGE = {
    "id": "BADGE-CORRUPTION-FIGHTER",
    "name": "For Contribution to the Fight Against Corruption",
    "description": (
        "Awarded for filing more than three reports at Tier 3 or higher "
        "that auditors have independently Verified."
    ),
}

CORRUPTION_FIGHTER_MIN_VERIFIED = 4  # strictly more than three
CORRUPTION_FIGHTER_MIN_TIER = 3


def verified_high_tier_count(db: Session, user: User) -> int:
    return (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .filter(Report.verification_status == "Verified")
        .filter(Report.tier >= CORRUPTION_FIGHTER_MIN_TIER)
        .count()
    )


def compute_badges(db: Session, user: User) -> list[dict]:
    badges: list[dict] = []
    count = verified_high_tier_count(db, user)
    if count >= CORRUPTION_FIGHTER_MIN_VERIFIED:
        badge = dict(CORRUPTION_FIGHTER_BADGE)
        badge["earned_count"] = count
        badges.append(badge)
    return badges
