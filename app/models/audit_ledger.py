from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLedger(Base):
    """Append-only ledger. Updates and deletes are rejected at the ORM layer
    to simulate an immutable log.

    The ledger records several event types:
      - POINTS_AWARDED  (Phase 4): user got points for a report
      - COI_BLOCK       (Phase 5): an auditor assignment was refused
      - RI_ADJUSTED     (Phase 7): a user's RI was bumped after verification
      - VOUCHER_USED    (Phase 6): voucher was redeemed (no PT after self-destruct)
    """

    __tablename__ = "audit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), default="POINTS_AWARDED", nullable=False, index=True)

    # Award fields (POINTS_AWARDED)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    report_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ri_at_award: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ri_multiplier: Mapped[float | None] = mapped_column(nullable=True)
    awarded_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free-form payload for non-award events (COI, RI, voucher)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


@event.listens_for(AuditLedger, "before_update", propagate=True)
def _block_update(mapper, connection, target):
    raise PermissionError("audit_ledger is append-only; updates are forbidden.")


@event.listens_for(AuditLedger, "before_delete", propagate=True)
def _block_delete(mapper, connection, target):
    raise PermissionError("audit_ledger is append-only; deletes are forbidden.")
