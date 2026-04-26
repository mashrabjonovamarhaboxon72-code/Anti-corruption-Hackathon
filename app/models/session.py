from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Session(Base):
    """Bearer session minted by /auth/recover.

    The pseudonymous_token remains the system's primary auth identifier.
    A session is a short-lived proof that "the citizen presented the
    mnemonic and the matching national_id at time T" — useful for
    rate-limiting and revocation distinct from the long-lived PT.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    pseudonymous_token: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
