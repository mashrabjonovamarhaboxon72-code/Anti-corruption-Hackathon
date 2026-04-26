"""Evidence integrity verification.

Recomputes the SHA-256 of the file at `evidence_path` and compares it to
the digest captured by the sanitizer at upload time. A match means no one
has touched the file on disk since it was cleansed; a mismatch (or a
missing file, or a path with no Evidence row) means the file's evidentiary
weight should be discounted.
"""

from pathlib import Path

from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.services.image_sanitizer import hash_file


def verify_evidence_integrity(db: Session, evidence_path: str | None) -> bool:
    if not evidence_path:
        return False

    record = db.query(Evidence).filter(Evidence.file_path == evidence_path).one_or_none()
    if record is None:
        return False

    current = hash_file(Path(evidence_path))
    if current is None:
        return False

    return current == record.integrity_hash
