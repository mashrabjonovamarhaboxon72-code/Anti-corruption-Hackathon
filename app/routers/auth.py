import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import DEFAULT_RELIABILITY_INDEX, SESSION_TTL_HOURS
from app.database import get_db
from app.models.audit_ledger import AuditLedger
from app.models.session import Session as SessionModel
from app.models.user import AGE_TIERS, User
from app.services.pseudonymous_token import generate_pseudonymous_token
from app.services.recovery import (
    MNEMONIC_WORD_COUNT,
    generate_mnemonic,
    hash_mnemonic,
    is_valid_mnemonic,
    verify_mnemonic,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    national_id: str = Field(..., min_length=1, description="Raw citizen ID. Never persisted.")
    age_tier: str = Field("Adult", description="Youth | Adult | Senior")


class RegisterResponse(BaseModel):
    pseudonymous_token: str
    reliability_index: int
    age_tier: str
    created: bool
    recovery_mnemonic: str | None = Field(
        None,
        description=(
            "24-word BIP39 recovery phrase. Returned ONLY on first creation; "
            "the server stores only its salted hash. Lose this and you lose "
            "your account."
        ),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.age_tier not in AGE_TIERS:
        raise HTTPException(status_code=400, detail=f"age_tier must be one of {AGE_TIERS}")

    try:
        pt = generate_pseudonymous_token(payload.national_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = db.query(User).filter(User.pseudonymous_token == pt).one_or_none()
    if existing:
        return RegisterResponse(
            pseudonymous_token=existing.pseudonymous_token,
            reliability_index=existing.reliability_index,
            age_tier=existing.age_tier,
            created=False,
            recovery_mnemonic=None,
        )

    mnemonic = generate_mnemonic()
    user = User(
        pseudonymous_token=pt,
        reliability_index=DEFAULT_RELIABILITY_INDEX,
        age_tier=payload.age_tier,
        recovery_hash=hash_mnemonic(mnemonic),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        pseudonymous_token=user.pseudonymous_token,
        reliability_index=user.reliability_index,
        age_tier=user.age_tier,
        created=True,
        recovery_mnemonic=mnemonic,
    )


class RecoverRequest(BaseModel):
    national_id: str = Field(..., min_length=1)
    mnemonic: str = Field(..., min_length=1, description=f"{MNEMONIC_WORD_COUNT}-word BIP39 phrase")


class RecoverResponse(BaseModel):
    pseudonymous_token: str
    session_token: str
    expires_at: str


def _audit_recovery(db: Session, *, user_id: int | None, success: bool, reason: str) -> None:
    db.add(
        AuditLedger(
            event_type="AUTH_RECOVERY_SUCCESS" if success else "AUTH_RECOVERY_FAILED",
            user_id=user_id,
            details={"reason": reason},
        )
    )


@router.post("/recover", response_model=RecoverResponse)
def recover(payload: RecoverRequest, db: Session = Depends(get_db)):
    """Re-issue a session given national_id + the recovery mnemonic.

    Failure responses are intentionally generic: the API must not reveal
    whether the failure was 'no such national_id' vs 'wrong mnemonic',
    because that distinction is itself a privacy leak (it confirms or
    denies registration of any queried national_id).
    """
    generic_failure = HTTPException(status_code=401, detail="Recovery failed.")

    try:
        pt = generate_pseudonymous_token(payload.national_id)
    except ValueError:
        # Bad national_id format — log nothing, no oracle to feed.
        raise generic_failure

    user = db.query(User).filter(User.pseudonymous_token == pt).one_or_none()

    # Even if the user is missing, run the mnemonic check to keep timing
    # roughly constant. We just compare against a dummy hash so an attacker
    # can't time-distinguish "user exists" from "user doesn't".
    dummy_hash = "0" * 64
    target_hash = user.recovery_hash if (user and user.recovery_hash) else dummy_hash

    if not is_valid_mnemonic(payload.mnemonic) or not verify_mnemonic(payload.mnemonic, target_hash):
        _audit_recovery(db, user_id=(user.id if user else None), success=False, reason="mnemonic_mismatch_or_unknown_id")
        db.commit()
        raise generic_failure

    # If we got here, user is real AND mnemonic matched. Issue session.
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    sess = SessionModel(
        session_token=session_token,
        pseudonymous_token=pt,
        expires_at=expires_at,
    )
    db.add(sess)
    _audit_recovery(db, user_id=user.id, success=True, reason="ok")
    db.commit()

    return RecoverResponse(
        pseudonymous_token=pt,
        session_token=session_token,
        expires_at=expires_at.isoformat() + "Z",
    )
