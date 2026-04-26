from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProtectionOrder(Base):
    """Digital Protection Order issued to a high-RI reporter who filed a
    verified Tier-4 report. The `payload` field stores the canonical JSON
    document that was signed; `signature` is its HMAC-SHA256.

    Each report yields at most one protection order (UNIQUE on report_id),
    so accidental re-verifications can't mint duplicates.
    """

    __tablename__ = "protection_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    pseudonymous_token: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), unique=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    signature: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
