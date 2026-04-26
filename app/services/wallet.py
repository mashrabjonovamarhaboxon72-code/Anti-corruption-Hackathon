import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_ledger import AuditLedger
from app.models.voucher import Voucher


def generate_voucher_code() -> str:
    """Human-readable, unguessable voucher code."""
    raw = secrets.token_urlsafe(9).upper().replace("-", "X").replace("_", "Y")
    return f"V-{raw[:4]}-{raw[4:8]}-{raw[8:12]}"


def issue_voucher(
    db: Session,
    *,
    pseudonymous_token: str,
    benefit: dict,
) -> Voucher:
    voucher = Voucher(
        code=generate_voucher_code(),
        benefit_id=benefit["id"],
        benefit_name=benefit["name"],
        points_cost=benefit["points_cost"],
        redeemer_pt=pseudonymous_token,
        status="Issued",
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return voucher


def self_destruct_transaction(db: Session, voucher: Voucher) -> Voucher:
    """Sever the PT↔voucher link.

    The voucher row survives so that audit aggregates (vouchers_used,
    benefits_distributed) still work, but no one — not even the operator —
    can later prove which citizen redeemed it.
    """
    if voucher.status != "Used":
        raise ValueError("self_destruct only runs against vouchers in status 'Used'.")

    severed_pt_prefix = (voucher.redeemer_pt or "")[:8]

    voucher.redeemer_pt = None
    voucher.self_destructed_at = datetime.utcnow()

    ledger = AuditLedger(
        event_type="VOUCHER_USED",
        details={
            "voucher_code": voucher.code,
            "benefit_id": voucher.benefit_id,
            "points_cost": voucher.points_cost,
            "severed_pt_prefix": severed_pt_prefix,
        },
    )
    db.add(ledger)
    db.commit()
    db.refresh(voucher)
    return voucher
