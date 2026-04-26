from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import DEFAULT_RELIABILITY_INDEX
from app.database import Base

AGE_TIERS = ("Youth", "Adult", "Senior")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pseudonymous_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reliability_index: Mapped[int] = mapped_column(Integer, default=DEFAULT_RELIABILITY_INDEX, nullable=False)
    points_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    age_tier: Mapped[str] = mapped_column(String(16), default="Adult", nullable=False)
    recovery_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
