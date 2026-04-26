from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assignment import Assignment
from app.models.audit_ledger import AuditLedger
from app.models.report import Report
from app.services.coi import evaluate_coi

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


class VerifyResponse(BaseModel):
    report_id: int
    verification_status: str


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
    db.commit()

    return VerifyResponse(report_id=report.id, verification_status=payload.verdict)
