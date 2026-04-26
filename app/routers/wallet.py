from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.voucher import Voucher
from app.routers.deps import get_current_pt
from app.services.badges import compute_badges
from app.services.benefits_catalog import benefits_for_tier, find_benefit
from app.services.wallet import issue_voucher, self_destruct_transaction

router = APIRouter(prefix="/wallet", tags=["wallet"])


class RewardsResponse(BaseModel):
    age_tier: str
    points_total: int
    benefits: list[dict]
    badges: list[dict]


@router.get("/rewards", response_model=RewardsResponse)
def list_rewards(
    pt: str = Depends(get_current_pt),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.pseudonymous_token == pt).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Session is valid but user record is missing.")
    return RewardsResponse(
        age_tier=user.age_tier,
        points_total=user.points_total,
        benefits=benefits_for_tier(user.age_tier),
        badges=compute_badges(db, user),
    )


class RedeemRequest(BaseModel):
    benefit_id: str


class RedeemResponse(BaseModel):
    voucher_code: str
    benefit_id: str
    benefit_name: str
    points_remaining: int


@router.post("/redeem", response_model=RedeemResponse, status_code=status.HTTP_201_CREATED)
def redeem(
    payload: RedeemRequest,
    pt: str = Depends(get_current_pt),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.pseudonymous_token == pt).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Session is valid but user record is missing.")

    benefit = find_benefit(payload.benefit_id)
    if benefit is None:
        raise HTTPException(status_code=404, detail="Unknown benefit_id.")
    if benefit["tier"] != user.age_tier:
        raise HTTPException(status_code=403, detail="Benefit is not available for your age tier.")
    if user.points_total < benefit["points_cost"]:
        raise HTTPException(status_code=402, detail="Insufficient points.")

    user.points_total -= benefit["points_cost"]
    voucher = issue_voucher(db, pseudonymous_token=pt, benefit=benefit)
    db.commit()
    db.refresh(user)

    return RedeemResponse(
        voucher_code=voucher.code,
        benefit_id=voucher.benefit_id,
        benefit_name=voucher.benefit_name,
        points_remaining=user.points_total,
    )


class UseRequest(BaseModel):
    voucher_code: str


class UseResponse(BaseModel):
    voucher_code: str
    status: str
    self_destructed: bool
    redeemer_pt: str | None


@router.post("/use", response_model=UseResponse)
def use_voucher(payload: UseRequest, db: Session = Depends(get_db)):
    """Mark a voucher as Used, then self-destruct the PT linkage.

    In a real deployment this endpoint would be called by the merchant /
    benefit provider, not the citizen — they'd scan the QR/code.
    """
    voucher = db.query(Voucher).filter(Voucher.code == payload.voucher_code).one_or_none()
    if voucher is None:
        raise HTTPException(status_code=404, detail="Unknown voucher_code.")
    if voucher.status == "Used":
        raise HTTPException(status_code=409, detail="Voucher already used.")

    from datetime import datetime as _dt

    voucher.status = "Used"
    voucher.used_at = _dt.utcnow()
    db.commit()
    db.refresh(voucher)

    voucher = self_destruct_transaction(db, voucher)

    return UseResponse(
        voucher_code=voucher.code,
        status=voucher.status,
        self_destructed=voucher.self_destructed_at is not None,
        redeemer_pt=voucher.redeemer_pt,
    )
