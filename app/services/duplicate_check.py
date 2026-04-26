from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import DUPLICATE_SIMILARITY_THRESHOLD
from app.models.report import Report
from app.services.embeddings import cosine_similarity, embed


@dataclass
class DuplicateCheckResult:
    embedding: list[float]
    is_duplicate: bool
    matched_report_id: int | None
    similarity: float


def check_for_duplicate(db: Session, text: str) -> DuplicateCheckResult:
    """Vectorize `text` and compare against every stored report's embedding.

    For a hackathon-scale corpus an in-memory linear scan is fine; if the
    reports table grows past a few thousand rows, swap this for pgvector or
    a dedicated ANN index.
    """
    new_vec = embed(text)

    best_id: int | None = None
    best_score = 0.0

    existing = db.query(Report.id, Report.embedding).all()
    for report_id, stored_vec in existing:
        if not stored_vec:
            continue
        score = cosine_similarity(new_vec, stored_vec)
        if score > best_score:
            best_score = score
            best_id = report_id

    is_dup = best_score >= DUPLICATE_SIMILARITY_THRESHOLD and best_id is not None

    return DuplicateCheckResult(
        embedding=new_vec,
        is_duplicate=is_dup,
        matched_report_id=best_id if is_dup else None,
        similarity=best_score,
    )
