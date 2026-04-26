"""Set required env vars before any app module is imported.

pytest loads conftest.py before test modules, so this guarantees
config.py sees the secrets even if a test file forgets to set them.
"""

import os

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
os.environ.setdefault("PROTECTION_ORDER_SIGNING_KEY", "test-protection-key-please-rotate")
os.environ.setdefault("RECOVERY_SALT", "test-recovery-salt-please-rotate")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest


@pytest.fixture(autouse=True)
def _reset_module_level_state():
    """Module-level singletons (rate limiters, stats cache) leak across tests.
    Reset them before every test so each starts from a clean slate."""
    try:
        from app.routers import auth as _auth
        _auth.recover_limiter.reset()
    except Exception:
        pass
    try:
        from app.services import public_stats as _ps
        _ps.get_cache().invalidate()
    except Exception:
        pass
    yield
