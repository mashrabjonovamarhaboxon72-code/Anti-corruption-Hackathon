from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Voucher(Base):
    """Issued reward voucher.

    `redeemer_pt` holds the citizen's pseudonymous token while the voucher
    is Issued. Once status flips to 'Used', `self_destruct_transaction`
    nulls `redeemer_pt` and stamps `self_destructed_at`. The voucher row
    survives for accounting, but the link back to the citizen is gone.
    """

    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    benefit_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    benefit_name: Mapped[str] = mapped_column(String(128), nullable=False)
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    redeemer_pt: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="Issued", nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    self_destructed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
