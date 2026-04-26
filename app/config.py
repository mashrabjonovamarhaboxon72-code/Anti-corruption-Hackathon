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

DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.88"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_RELIABILITY_INDEX = 500
RI_BASELINE = 500
