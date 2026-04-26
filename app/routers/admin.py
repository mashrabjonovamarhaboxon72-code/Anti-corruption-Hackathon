from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assignment import Assignment
from app.models.audit_ledger import AuditLedger
from app.models.report import Report
from app.models.user import User
from app.services.coi import evaluate_coi
from app.services.evidence_integrity import verify_evidence_integrity
from app.services.priority import evaluate_priority
from app.services.protection_order import maybe_issue as maybe_issue_protection_order

router = APIRouter(prefix="/admin", tags=["admin"])


class AssignRequest(BaseModel):
    auditor_id: str = Field(..., min_length=1)
    report_id: int = Field(..., ge=1)


class AssignResponse(BaseModel):
    assigned: bool
    assignment_id: int | None
    blocked_reason: str | None
    matched_relatives: list[str]
    auditor_department: str | None
    target_department: str | None


@router.post("/assign", response_model=AssignResponse)
def assign(payload: AssignRequest, db: Session = Depends(get_db)):
    report = db.get(Report, payload.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown report_id.")

    decision = evaluate_coi(
        auditor_id=payload.auditor_id,
        report_text=report.text,
        target_department_id=report.target_department_id,
    )

    if decision.blocked:
        ledger = AuditLedger(
            event_type="COI_BLOCK",
            user_id=report.user_id,
            report_id=report.id,
            details={
                "auditor_id": payload.auditor_id,
                "reason": decision.reason,
                "matched_relatives": decision.matched_relatives,
                "auditor_department": decision.auditor_department,
                "target_department": decision.target_department,
            },
        )
        db.add(ledger)
        db.commit()
        return AssignResponse(
            assigned=False,
            assignment_id=None,
            blocked_reason=decision.reason,
            matched_relatives=decision.matched_relatives,
            auditor_department=decision.auditor_department,
            target_department=decision.target_department,
        )

    assignment = Assignment(auditor_id=payload.auditor_id, report_id=report.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return AssignResponse(
        assigned=True,
        assignment_id=assignment.id,
        blocked_reason=None,
        matched_relatives=[],
        auditor_department=decision.auditor_department,
        target_department=decision.target_department,
    )


class VerifyRequest(BaseModel):
    auditor_id: str
    report_id: int
    verdict: str = Field(..., description="Verified | Malicious")


class ProtectionOrderSummary(BaseModel):
    order_id: str
    payload: dict
    signature: str


class VerifyResponse(BaseModel):
    report_id: int
    verification_status: str
    is_media_priority: bool
    trust_score: float
    protection_order: ProtectionOrderSummary | None = None


@router.post("/verify", response_model=VerifyResponse, status_code=status.HTTP_202_ACCEPTED)
def verify(payload: VerifyRequest, db: Session = Depends(get_db)):
    if payload.verdict not in {"Verified", "Malicious"}:
        raise HTTPException(status_code=400, detail="verdict must be 'Verified' or 'Malicious'")

    report = db.get(Report, payload.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown report_id.")

    assigned = (
        db.query(Assignment)
        .filter(Assignment.report_id == payload.report_id, Assignment.auditor_id == payload.auditor_id)
        .first()
    )
    if assigned is None:
        raise HTTPException(status_code=403, detail="Auditor is not assigned to this report.")

    report.verification_status = payload.verdict
    report.ri_applied = False

    reporter = db.get(User, report.user_id)
    priority = evaluate_priority(
        tier=report.tier,
        reliability_index=reporter.reliability_index if reporter else 0,
        similarity=report.similarity_score,
        evidence_verified=verify_evidence_integrity(db, report.evidence_path),
        has_target_department=bool(report.target_department_id),
        verification_status=payload.verdict,
    )
    report.trust_score = priority.trust_score
    report.is_media_priority = priority.is_media_priority and report.status == "Accepted"

    db.commit()
    db.refresh(report)

    issued = None
    if reporter is not None:
        issued = maybe_issue_protection_order(
            db,
            user=reporter,
            report=report,
            auditor_id=payload.auditor_id,
            verdict=payload.verdict,
        )

    return VerifyResponse(
        report_id=report.id,
        verification_status=payload.verdict,
        is_media_priority=report.is_media_priority,
        trust_score=report.trust_score,
        protection_order=(
            ProtectionOrderSummary(
                order_id=issued.order_id,
                payload=issued.payload,
                signature=issued.signature,
            )
            if issued is not None
            else None
        ),
    )


class MediaFeedItem(BaseModel):
    report_id: int
    tier: int
    trust_score: float
    target_department_id: str | None
    verification_status: str | None
    text: str
    created_at: str


class MediaFeedResponse(BaseModel):
    count: int
    reports: list[MediaFeedItem]


@router.get("/media-feed", response_model=MediaFeedResponse)
def media_feed(limit: int = 50, db: Session = Depends(get_db)):
    """Public-transparency feed.

    Lists only reports flagged is_media_priority=True (Tier 3/4 with
    trust_score > 0.9, never duplicates, never Malicious-marked). The
    reporter's pseudonymous_token is deliberately excluded — broadcasts
    must not link content back to a citizen even via PT.
    """
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")

    rows = (
        db.query(Report)
        .filter(Report.is_media_priority.is_(True))
        .order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )

    items = [
        MediaFeedItem(
            report_id=r.id,
            tier=r.tier,
            trust_score=r.trust_score,
            target_department_id=r.target_department_id,
            verification_status=r.verification_status,
            text=r.text,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
    return MediaFeedResponse(count=len(items), reports=items)
