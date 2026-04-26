import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/integrity_shield",
)

PT_SALT = os.environ.get("PT_SALT")
if not PT_SALT:
    raise RuntimeError(
        "PT_SALT environment variable is required. "
        "Set it to a long random secret; rotating it invalidates all pseudonymous tokens."
    )

PROTECTION_ORDER_SIGNING_KEY = os.environ.get("PROTECTION_ORDER_SIGNING_KEY")
if not PROTECTION_ORDER_SIGNING_KEY:
    raise RuntimeError(
        "PROTECTION_ORDER_SIGNING_KEY environment variable is required. "
        "Use a different value than PT_SALT — key separation prevents "
        "compromise of one secret from invalidating the other."
    )

RECOVERY_SALT = os.environ.get("RECOVERY_SALT")
if not RECOVERY_SALT:
    raise RuntimeError(
        "RECOVERY_SALT environment variable is required. "
        "Use a different value than PT_SALT and PROTECTION_ORDER_SIGNING_KEY — "
        "key separation prevents one compromise from collapsing the others."
    )

SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))

# /admin/demo-setup wipes the entire data plane. It must NEVER ship enabled
# in production. Default off; flip with DEMO_MODE=1 only on demo machines.
DEMO_MODE = os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.88"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_RELIABILITY_INDEX = 500
RI_BASELINE = 500

PUBLIC_STATS_TTL_SECONDS = int(os.getenv("PUBLIC_STATS_TTL_SECONDS", "60"))
PUBLIC_STATS_RECENT_BADGES_LIMIT = int(os.getenv("PUBLIC_STATS_RECENT_BADGES_LIMIT", "10"))
