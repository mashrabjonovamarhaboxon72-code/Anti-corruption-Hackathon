"""Shared FastAPI dependencies.

`get_current_pt` is the bearer-session auth check used by every endpoint
that previously consumed a raw pseudonymous_token from the request body
or query string. Callers must first run /auth/recover (or /auth/register
in a future flow that issues a session) and then send
`Authorization: Bearer <session_token>` on subsequent requests.
"""

from datetime import datetime

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.session import Session as SessionModel

_INVALID = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired session.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_pt(
    authorization: str | None = Header(
        default=None,
        description="Bearer <session_token> minted by /auth/recover.",
    ),
    db: DBSession = Depends(get_db),
) -> str:
    if not authorization:
        raise _INVALID

    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise _INVALID

    token = parts[1].strip()
    if not token:
        raise _INVALID

    sess = (
        db.query(SessionModel)
        .filter(SessionModel.session_token == token)
        .one_or_none()
    )
    if sess is None or sess.revoked_at is not None or sess.expires_at <= datetime.utcnow():
        raise _INVALID

    return sess.pseudonymous_token
