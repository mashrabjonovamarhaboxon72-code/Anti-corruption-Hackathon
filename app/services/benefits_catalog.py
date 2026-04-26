"""Static benefits catalog. In production this would be a managed CMS or DB
table; for the hackathon we keep it as a Python constant so the demo can be
re-seeded deterministically."""

from typing import Iterable

BENEFITS: list[dict] = [
    {"id": "BEN-TRANSPORT-50", "name": "Public Transport Subsidy 50%", "tier": "Youth", "points_cost": 200},
    {"id": "BEN-LIBRARY", "name": "National Library Annual Pass", "tier": "Youth", "points_cost": 150},
    {"id": "BEN-TAX-REBATE-100", "name": "Tax Rebate (100,000 UZS)", "tier": "Adult", "points_cost": 500},
    {"id": "BEN-TRANSIT-CARD", "name": "Annual Transit Card", "tier": "Adult", "points_cost": 350},
    {"id": "BEN-HEALTH-VOUCHER", "name": "Healthcare Visit Voucher", "tier": "Senior", "points_cost": 250},
    {"id": "BEN-UTILITY-20", "name": "Utility Bill Discount 20%", "tier": "Senior", "points_cost": 300},
]


def benefits_for_tier(age_tier: str) -> list[dict]:
    return [b for b in BENEFITS if b["tier"] == age_tier]


def find_benefit(benefit_id: str) -> dict | None:
    for b in BENEFITS:
        if b["id"] == benefit_id:
            return b
    return None


def all_tiers() -> Iterable[str]:
    return sorted({b["tier"] for b in BENEFITS})
