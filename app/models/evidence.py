from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Evidence(Base):
    """Sanitized evidence file with an integrity anchor.

    `integrity_hash` is the SHA-256 of the bytes written by the sanitizer.
    Any later read of the file is expected to re-hash to the same value;
    if it doesn't, the file has been tampered with and downstream services
    (e.g. ReportPriorityService) should refuse to credit it.
    """

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    integrity_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
