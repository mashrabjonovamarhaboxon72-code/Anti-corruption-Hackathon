from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Accepted", nullable=False)
    duplicate_of: Mapped[int | None] = mapped_column(Integer, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    evidence_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    target_department_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    verification_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ri_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
