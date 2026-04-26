import os
import sys
from io import BytesIO
from pathlib import Path

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).resolve().parent / "_tmp_uploads_evi"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database

test_engine = create_engine("sqlite:///:memory:", future=True)
database.engine = test_engine
database.SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

from app.database import Base, SessionLocal  # noqa: E402
from app.models.evidence import Evidence  # noqa: E402
from app.services.evidence_integrity import verify_evidence_integrity  # noqa: E402
from app.services.image_sanitizer import hash_file, sanitize_and_store  # noqa: E402


def setup_module(module):
    Base.metadata.create_all(bind=test_engine)


def _png_bytes(color=(10, 20, 30)) -> bytes:
    img = Image.new("RGB", (16, 16), color=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _persist(sanitized) -> Evidence:
    db = SessionLocal()
    e = Evidence(
        file_path=str(sanitized.path),
        integrity_hash=sanitized.sha256_hash,
        format=sanitized.format,
        size_bytes=sanitized.size_bytes,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    db.close()
    return e


def test_sanitizer_returns_hash_matching_file_on_disk():
    sanitized = sanitize_and_store(_png_bytes(), "x.png")
    assert len(sanitized.sha256_hash) == 64
    assert hash_file(sanitized.path) == sanitized.sha256_hash
    sanitized.path.unlink()


def test_sanitizer_hash_is_deterministic_for_identical_pixels():
    a = sanitize_and_store(_png_bytes(color=(50, 60, 70)), "a.png")
    b = sanitize_and_store(_png_bytes(color=(50, 60, 70)), "b.png")
    # Same pixels through the same pipeline → same digest, even though
    # the on-disk filenames differ (random suffix).
    assert a.sha256_hash == b.sha256_hash
    assert a.path != b.path
    a.path.unlink()
    b.path.unlink()


def test_verify_returns_true_for_unmodified_file():
    sanitized = sanitize_and_store(_png_bytes(color=(11, 22, 33)), "ok.png")
    _persist(sanitized)
    db = SessionLocal()
    assert verify_evidence_integrity(db, str(sanitized.path)) is True
    db.close()
    sanitized.path.unlink()


def test_verify_returns_false_when_file_tampered():
    sanitized = sanitize_and_store(_png_bytes(color=(99, 99, 99)), "tamper.png")
    _persist(sanitized)

    # Append a byte — file no longer matches stored hash.
    with sanitized.path.open("ab") as fh:
        fh.write(b"X")

    db = SessionLocal()
    assert verify_evidence_integrity(db, str(sanitized.path)) is False
    db.close()
    sanitized.path.unlink()


def test_verify_returns_false_when_file_deleted():
    sanitized = sanitize_and_store(_png_bytes(color=(1, 2, 3)), "gone.png")
    _persist(sanitized)
    sanitized.path.unlink()

    db = SessionLocal()
    assert verify_evidence_integrity(db, str(sanitized.path)) is False
    db.close()


def test_verify_returns_false_for_unknown_path():
    db = SessionLocal()
    assert verify_evidence_integrity(db, "uploads/never_uploaded.png") is False
    assert verify_evidence_integrity(db, None) is False
    assert verify_evidence_integrity(db, "") is False
    db.close()
