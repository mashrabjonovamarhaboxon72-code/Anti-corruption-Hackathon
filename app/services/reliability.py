"""Reliability Index (RI) recalculation.

Pulls reports whose `verification_status` has been set but not yet applied
to the reporter's RI, applies the delta, marks the report as `ri_applied`,
and writes an immutable RI_ADJUSTED row to the audit ledger.

Verdicts:
  Verified  → +50 RI (capped at 1000)
  Malicious → −150 RI (floored at 0)

The `scoring` service already reads `user.reliability_index` at award time,
so updates here automatically influence the next point award.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.audit_ledger import AuditLedger
from app.models.report import Report
from app.models.user import User

RI_DELTA = {"Verified": 50, "Malicious": -150}
RI_MIN = 0
RI_MAX = 1000


@dataclass
class RIChange:
    user_id: int
    report_id: int
    verdict: str
    ri_before: int
    ri_after: int
    delta: int


def recalculate_pending(db: Session) -> list[RIChange]:
    """Process every Report with a verdict that hasn't been folded into RI.

    Idempotent: each report flips `ri_applied=True` after one application,
    so re-running this against the same data is a no-op.
    """
    changes: list[RIChange] = []

    pending = (
        db.query(Report)
        .filter(Report.verification_status.in_(("Verified", "Malicious")))
        .filter(Report.ri_applied.is_(False))
        .all()
    )

    for report in pending:
        verdict = report.verification_status
        delta = RI_DELTA.get(verdict, 0)
        if delta == 0:
            continue

        user = db.get(User, report.user_id)
        if user is None:
            report.ri_applied = True
            continue

        ri_before = user.reliability_index
        ri_after = max(RI_MIN, min(RI_MAX, ri_before + delta))
        actual_delta = ri_after - ri_before

        user.reliability_index = ri_after
        report.ri_applied = True

        ledger = AuditLedger(
            event_type="RI_ADJUSTED",
            user_id=user.id,
            report_id=report.id,
            details={
                "verdict": verdict,
                "ri_before": ri_before,
                "ri_after": ri_after,
                "delta_requested": delta,
                "delta_applied": actual_delta,
            },
        )
        db.add(ledger)

        changes.append(
            RIChange(
                user_id=user.id,
                report_id=report.id,
                verdict=verdict,
                ri_before=ri_before,
                ri_after=ri_after,
                delta=actual_delta,
            )
        )

    if changes:
        db.commit()

    return changes
