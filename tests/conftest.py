"""Set required env vars before any app module is imported.

pytest loads conftest.py before test modules, so this guarantees
config.py sees the secrets even if a test file forgets to set them.
"""

import os

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
os.environ.setdefault("PROTECTION_ORDER_SIGNING_KEY", "test-protection-key-please-rotate")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
