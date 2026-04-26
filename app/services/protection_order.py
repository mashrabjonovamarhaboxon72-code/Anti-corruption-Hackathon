"""ProtectionOrderService.

Auto-issues a Digital Protection Order when a report is verified Tier-4
AND the submitter's Reliability Index is above 900. The order is a
canonical JSON document signed with HMAC-SHA256 using a key that is
*separate* from PT_SALT — compromising one secret does not invalidate
the other.

The signed payload is intentionally minimal: order_id, the reporter's
pseudonymous token (no national ID, ever), the report id and tier, the
auditor who confirmed, issued/expiry timestamps, and jurisdiction. A
verifier rebuilds the same canonical JSON from the stored payload, runs
HMAC-SHA256 with the shared key, and compares against `signature`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import PROTECTION_ORDER_SIGNING_KEY
from app.models.audit_ledger import AuditLedger
from app.models.protection_order import ProtectionOrder
from app.models.report import Report
from app.models.user import User

PROTECTION_RI_THRESHOLD = 900
PROTECTION_TIER = 4
PROTECTION_VALIDITY_DAYS = 365
JURISDICTION = "UZ-NATIONAL"


@dataclass
class IssuedOrder:
    order_id: str
    payload: dict
    signature: str


def _canonical(payload: dict) -> bytes:
    """Stable byte representation for signing.

    `sort_keys=True` + `separators=(",",":")` removes whitespace and key
    ordering as variables, so the same logical payload always produces
    the same bytes — and the same HMAC.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_payload(payload: dict) -> str:
    return hmac.new(
        PROTECTION_ORDER_SIGNING_KEY.encode("utf-8"),
        _canonical(payload),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: dict, signature: str) -> bool:
    expected = sign_payload(payload)
    return hmac.compare_digest(expected, signature)


def _build_payload(*, order_id: str, user: User, report: Report, auditor_id: str) -> dict:
    issued = datetime.utcnow()
    return {
        "order_id": order_id,
        "kind": "DIGITAL_PROTECTION_ORDER",
        "version": 1,
        "jurisdiction": JURISDICTION,
        "pseudonymous_token": user.pseudonymous_token,
        "report_id": report.id,
        "tier": report.tier,
        "verified_by_auditor": auditor_id,
        "ri_at_issue": user.reliability_index,
        "issued_at": issued.isoformat() + "Z",
        "valid_until": (issued + timedelta(days=PROTECTION_VALIDITY_DAYS)).isoformat() + "Z",
    }


def maybe_issue(
    db: Session,
    *,
    user: User,
    report: Report,
    auditor_id: str,
    verdict: str,
) -> IssuedOrder | None:
    """Issue a protection order if all conditions are met. No-op otherwise.

    Conditions:
      - verdict is "Verified"
      - report.tier == PROTECTION_TIER (4)
      - user.reliability_index > PROTECTION_RI_THRESHOLD (900)
      - no existing order already issued for this report
    """
    if verdict != "Verified":
        return None
    if report.tier != PROTECTION_TIER:
        return None
    if user.reliability_index <= PROTECTION_RI_THRESHOLD:
        return None

    already = (
        db.query(ProtectionOrder)
        .filter(ProtectionOrder.report_id == report.id)
        .one_or_none()
    )
    if already is not None:
        return IssuedOrder(
            order_id=already.order_id,
            payload=already.payload,
            signature=already.signature,
        )

    order_id = f"DPO-{datetime.utcnow().strftime('%Y%m%d')}-{secrets.token_hex(6).upper()}"
    payload = _build_payload(order_id=order_id, user=user, report=report, auditor_id=auditor_id)
    signature = sign_payload(payload)

    record = ProtectionOrder(
        order_id=order_id,
        pseudonymous_token=user.pseudonymous_token,
        report_id=report.id,
        payload=payload,
        signature=signature,
    )
    db.add(record)

    db.add(
        AuditLedger(
            event_type="PROTECTION_ORDER_ISSUED",
            user_id=user.id,
            report_id=report.id,
            details={
                "order_id": order_id,
                "tier": report.tier,
                "ri_at_issue": user.reliability_index,
                "auditor_id": auditor_id,
                "signature_prefix": signature[:16],
            },
        )
    )
    db.commit()

    return IssuedOrder(order_id=order_id, payload=payload, signature=signature)
