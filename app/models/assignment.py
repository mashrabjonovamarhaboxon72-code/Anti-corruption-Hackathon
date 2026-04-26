from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="Active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
