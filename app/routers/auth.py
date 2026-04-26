from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import DEFAULT_RELIABILITY_INDEX
from app.database import get_db
from app.models.user import User
from app.services.pseudonymous_token import generate_pseudonymous_token

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    national_id: str = Field(..., min_length=1, description="Raw citizen ID. Never persisted.")


class RegisterResponse(BaseModel):
    pseudonymous_token: str
    reliability_index: int
    created: bool


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        pt = generate_pseudonymous_token(payload.national_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = db.query(User).filter(User.pseudonymous_token == pt).one_or_none()
    if existing:
        return RegisterResponse(
            pseudonymous_token=existing.pseudonymous_token,
            reliability_index=existing.reliability_index,
            created=False,
        )

    user = User(pseudonymous_token=pt, reliability_index=DEFAULT_RELIABILITY_INDEX)
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        pseudonymous_token=user.pseudonymous_token,
        reliability_index=user.reliability_index,
        created=True,
    )
