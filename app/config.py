import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/integrity_shield",
)

# Render's managed Postgres (and Heroku's, and a few others) hand out
# connection strings prefixed `postgres://`. SQLAlchemy 2.x dropped support
# for that scheme — only `postgresql://` and `postgresql+driver://` work.
# Rewriting here so a vanilla `DATABASE_URL` from the platform Just Works
# without operators having to remember the driver-prefix gotcha.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgres://") :]
elif DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL.split("://", 1)[0]:
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://") :]

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

# Brute-force safeguard for /auth/recover.
RATE_LIMIT_RECOVER_MAX_ATTEMPTS = int(os.getenv("RATE_LIMIT_RECOVER_MAX_ATTEMPTS", "5"))
RATE_LIMIT_RECOVER_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_RECOVER_WINDOW_SECONDS", str(15 * 60)))

# NOTE: CORS allow_origins is read directly from FRONTEND_URL in app/main.py
# so the multi-cloud deploy story is "set FRONTEND_URL on Render to your
# Vercel URL, done." See app/main.py for the single-source-of-truth read.

# /admin/demo-setup wipes the entire data plane. It must NEVER ship enabled
# in production. Default off; flip with DEMO_MODE=1 only on demo machines.
DEMO_MODE = os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.88"))

# Default embedder picked for cost: all-MiniLM-L6-v2 weights ~80 MB and
# fits in 512 MB RAM (Render free tier). The larger all-mpnet-base-v2
# (~420 MB) gives slightly better embeddings but blows the free-tier
# memory budget. Override via env if you have the headroom.
#
# IMPORTANT: switching models also changes the embedding dimensionality
# (MiniLM → 384, mpnet → 768). cosine_similarity will raise on shape
# mismatch when comparing vectors written under different models, so a
# model swap effectively invalidates every previously-stored Report.embedding.
# For a fresh deploy this is a non-issue; for a live system, re-embed all
# reports (or run the two models side-by-side during a migration window).
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_RELIABILITY_INDEX = 500
RI_BASELINE = 500

PUBLIC_STATS_TTL_SECONDS = int(os.getenv("PUBLIC_STATS_TTL_SECONDS", "60"))
PUBLIC_STATS_RECENT_BADGES_LIMIT = int(os.getenv("PUBLIC_STATS_RECENT_BADGES_LIMIT", "10"))
