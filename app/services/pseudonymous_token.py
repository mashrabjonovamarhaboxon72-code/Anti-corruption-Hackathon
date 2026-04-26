import hashlib
import hmac

from app.config import PT_SALT


def generate_pseudonymous_token(national_id: str) -> str:
    """Return an HMAC-SHA256 of the national_id keyed by the server-side salt.

    HMAC is used instead of plain SHA-256(salt || id) so that, even if the
    hash output leaks, the salt remains computationally hidden, defeating
    length-extension and rainbow-table attacks against the relatively
    low-entropy national_id space.
    """
    if not isinstance(national_id, str) or not national_id.strip():
        raise ValueError("national_id must be a non-empty string")

    normalized = national_id.strip()
    return hmac.new(
        PT_SALT.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
