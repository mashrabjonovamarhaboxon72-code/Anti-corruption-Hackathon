"""BIP39 mnemonic generation + recovery hash verification.

The mnemonic is the user's only path back to their pseudonymous identity:
losing it means losing the account. We generate 24 words (256 bits of
entropy) and hash them with HMAC-SHA256 keyed by RECOVERY_SALT. The
hash is what we persist; the cleartext mnemonic is shown to the user
exactly once in the /auth/register response and never stored.

Why HMAC over plain SHA-256(salt || mnemonic):
  - Length-extension immunity (academic for 24 words but free).
  - Compromising the recovery_hash dump alone yields no usable input
    for an offline attack against the mnemonic without also stealing
    RECOVERY_SALT.

Verification uses hmac.compare_digest for constant-time comparison so
timing-side-channel oracles can't distinguish "correct prefix" from
"incorrect prefix" responses.
"""

from __future__ import annotations

import hashlib
import hmac

from mnemonic import Mnemonic

from app.config import RECOVERY_SALT

_mnemo = Mnemonic("english")
MNEMONIC_WORD_COUNT = 24
MNEMONIC_STRENGTH_BITS = 256  # 24 words = 256 bits of entropy in BIP39


def generate_mnemonic() -> str:
    return _mnemo.generate(strength=MNEMONIC_STRENGTH_BITS)


def _normalize(mnemonic: str) -> str:
    """Collapse whitespace and lowercase. BIP39 wordlist is lowercase, so
    case-folding here lets users paste from anywhere without losing the
    match. This must be applied identically at hash-time and verify-time."""
    return " ".join(mnemonic.strip().lower().split())


def hash_mnemonic(mnemonic: str) -> str:
    return hmac.new(
        RECOVERY_SALT.encode("utf-8"),
        _normalize(mnemonic).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def is_valid_mnemonic(mnemonic: str) -> bool:
    """BIP39 checksum validation. False for garbage input; lets the
    recovery endpoint short-circuit without doing a hash comparison."""
    try:
        return _mnemo.check(_normalize(mnemonic))
    except Exception:
        return False


def verify_mnemonic(mnemonic: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_mnemonic(mnemonic), stored_hash)
