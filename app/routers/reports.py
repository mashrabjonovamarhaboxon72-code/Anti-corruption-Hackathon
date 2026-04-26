from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report
from app.models.user import User
from app.services.duplicate_check import check_for_duplicate
from app.services.evidence_integrity import verify_evidence_integrity
from app.services.priority import evaluate_priority
from app.services.scoring import CORRUPTION_TIERS, award_points

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    pseudonymous_token: str = Field(..., min_length=64, max_length=64)
    text: str = Field(..., min_length=10)
    tier: int = Field(..., ge=1, le=4)
    evidence_path: str | None = None
    target_department_id: str | None = Field(None, description="Department being reported (for COI checks).")


class ReportResponse(BaseModel):
    report_id: int
    status: str
    similarity: float
    duplicate_of: int | None
    awarded_points: int
    ri_multiplier: float
    user_points_total: int
    trust_score: float
    is_media_priority: bool


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def submit_report(payload: ReportRequest, db: Session = Depends(get_db)):
    if payload.tier not in CORRUPTION_TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {sorted(CORRUPTION_TIERS)}")

    user = db.query(User).filter(User.pseudonymous_token == payload.pseudonymous_token).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Unknown pseudonymous_token. Register first.")

    dup = check_for_duplicate(db, payload.text)

    evidence_verified = verify_evidence_integrity(db, payload.evidence_path)

    priority = evaluate_priority(
        tier=payload.tier,
        reliability_index=user.reliability_index,
        similarity=dup.similarity,
        evidence_verified=evidence_verified,
        has_target_department=bool(payload.target_department_id),
    )

    # Duplicates are never broadcast even if they would otherwise qualify.
    is_priority = priority.is_media_priority and not dup.is_duplicate

    report = Report(
        user_id=user.id,
        text=payload.text,
        tier=payload.tier,
        embedding=dup.embedding,
        status="Potential Duplicate" if dup.is_duplicate else "Accepted",
        duplicate_of=dup.matched_report_id,
        similarity_score=dup.similarity,
        evidence_path=payload.evidence_path,
        target_department_id=payload.target_department_id,
        trust_score=priority.trust_score,
        is_media_priority=is_priority,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    awarded = 0
    multiplier = 0.0
    if not dup.is_duplicate:
        award = award_points(db, user=user, report_id=report.id, tier=payload.tier)
        awarded = award.awarded_points
        multiplier = award.ri_multiplier
        db.refresh(user)

    return ReportResponse(
        report_id=report.id,
        status=report.status,
        similarity=dup.similarity,
        duplicate_of=report.duplicate_of,
        awarded_points=awarded,
        ri_multiplier=multiplier,
        user_points_total=user.points_total,
        trust_score=report.trust_score,
        is_media_priority=report.is_media_priority,
    )
