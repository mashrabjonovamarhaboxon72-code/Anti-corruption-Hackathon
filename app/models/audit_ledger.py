from datetime import datetime

from sqlalchemy import DateTime, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLedger(Base):
    """Append-only ledger. Updates and deletes are rejected at the ORM layer
    to simulate an immutable log."""

    __tablename__ = "audit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    report_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    base_points: Mapped[int] = mapped_column(Integer, nullable=False)
    ri_at_award: Mapped[int] = mapped_column(Integer, nullable=False)
    ri_multiplier: Mapped[float] = mapped_column(nullable=False)
    awarded_points: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), default="POINTS_AWARDED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


@event.listens_for(AuditLedger, "before_update", propagate=True)
def _block_update(mapper, connection, target):
    raise PermissionError("audit_ledger is append-only; updates are forbidden.")


@event.listens_for(AuditLedger, "before_delete", propagate=True)
def _block_delete(mapper, connection, target):
    raise PermissionError("audit_ledger is append-only; deletes are forbidden.")
