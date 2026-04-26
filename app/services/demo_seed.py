"""Demo seeding helpers used by /admin/demo-setup.

Two responsibilities:
  - reset_database(): nuke every data table so the demo starts from a
    known state. Uses Core-level table.delete() rather than the ORM so
    the audit_ledger immutability listener is bypassed (the listener
    only fires on ORM-tracked instance deletes).
  - seed_demo_state(): plant a Whistleblower citizen, three baseline
    reports across different departments, and one cleansed evidence
    image. Returns a dict the endpoint hands straight back to the
    presenter so they know what to demo.

The embedder is injected so tests can avoid loading the 420MB
sentence-transformer model. The endpoint passes the real one.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from io import BytesIO
from typing import Callable

from PIL import Image
from sqlalchemy.orm import Session as DBSession

from app.config import DEFAULT_RELIABILITY_INDEX, SESSION_TTL_HOURS
from app.database import Base
from app.models.evidence import Evidence
from app.models.report import Report
from app.models.session import Session as SessionModel
from app.models.user import User
from app.services.image_sanitizer import sanitize_and_store
from app.services.priority import evaluate_priority
from app.services.pseudonymous_token import generate_pseudonymous_token
from app.services.recovery import generate_mnemonic, hash_mnemonic

WHISTLEBLOWER_NATIONAL_ID = "DEMO-WHISTLEBLOWER-001"
WHISTLEBLOWER_RI = 950

BASELINE_REPORTS: list[dict] = [
    {
        "department": "DEPT-CUSTOMS",
        "tier": 4,
        "text": (
            "Senior customs inspector at Tashkent airport terminal 3 demanded "
            "5,000,000 UZS to release a personal shipment without inspection."
        ),
    },
    {
        "department": "DEPT-TRAFFIC-POLICE",
        "tier": 2,
        "text": (
            "Traffic officer on Amir Temur avenue refused to issue an official "
            "ticket for a fabricated violation unless paid 200,000 UZS in cash."
        ),
    },
    {
        "department": "DEPT-EDUCATION",
        "tier": 3,
        "text": (
            "University admissions clerk asked applicants for an unofficial "
            "'expediting fee' of 1,500,000 UZS to process entrance documents."
        ),
    },
]


def reset_database(db: DBSession) -> dict:
    """Truncate every data table. Returns counts of rows removed per table.

    Files on disk referenced by Evidence rows are unlinked first so /uploads
    doesn't accumulate orphans across demo cycles.
    """
    from pathlib import Path

    counts: dict[str, int] = {}

    # Best-effort file cleanup before we lose the path references.
    try:
        for ev in db.query(Evidence).all():
            p = Path(ev.file_path)
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass
    except Exception:
        # If the table doesn't exist yet (fresh DB) we just skip the cleanup.
        pass

    for table in reversed(Base.metadata.sorted_tables):
        result = db.execute(table.delete())
        counts[table.name] = result.rowcount or 0
    db.commit()
    return counts


def _seed_whistleblower(db: DBSession) -> tuple[User, str, str]:
    pt = generate_pseudonymous_token(WHISTLEBLOWER_NATIONAL_ID)
    mnemonic = generate_mnemonic()
    user = User(
        pseudonymous_token=pt,
        reliability_index=WHISTLEBLOWER_RI,
        age_tier="Adult",
        recovery_hash=hash_mnemonic(mnemonic),
    )
    db.add(user)
    db.flush()

    session_token = secrets.token_urlsafe(32)
    sess = SessionModel(
        session_token=session_token,
        pseudonymous_token=pt,
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(sess)
    db.flush()
    db.refresh(user)

    return user, mnemonic, session_token


def _seed_baselines(db: DBSession, user: User, embedder: Callable[[str], list[float]]) -> list[dict]:
    seeded: list[dict] = []
    for spec in BASELINE_REPORTS:
        embedding = embedder(spec["text"])
        priority = evaluate_priority(
            tier=spec["tier"],
            reliability_index=user.reliability_index,
            similarity=0.0,
            evidence_verified=False,  # baselines have no evidence yet
            has_target_department=True,
        )
        report = Report(
            user_id=user.id,
            text=spec["text"],
            tier=spec["tier"],
            embedding=embedding,
            status="Accepted",
            similarity_score=0.0,
            target_department_id=spec["department"],
            trust_score=priority.trust_score,
            is_media_priority=priority.is_media_priority,
        )
        db.add(report)
        db.flush()
        seeded.append(
            {
                "report_id": report.id,
                "department": spec["department"],
                "tier": spec["tier"],
                "text": spec["text"],
                "trust_score": report.trust_score,
                "is_media_priority": report.is_media_priority,
            }
        )
    return seeded


def _make_demo_image_with_exif() -> bytes:
    """Synthesize a small JPEG carrying EXIF + GPS markers so the sanitizer
    has something visible to strip when the presenter inspects the file."""
    img = Image.new("RGB", (96, 96), color=(40, 120, 200))
    exif = img.getexif()
    exif[0x010F] = "DemoCorp Camera Co."
    exif[0x0110] = "ModelX-GPS"
    exif[0x9003] = "2026:04:26 10:00:00"
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92, exif=exif.tobytes())
    return buf.getvalue()


def _seed_evidence(db: DBSession) -> dict:
    raw = _make_demo_image_with_exif()
    sanitized = sanitize_and_store(raw, "demo_evidence.jpg")
    evidence = Evidence(
        file_path=str(sanitized.path),
        integrity_hash=sanitized.sha256_hash,
        format=sanitized.format,
        size_bytes=sanitized.size_bytes,
    )
    db.add(evidence)
    db.flush()
    return {
        "evidence_id": evidence.id,
        "file_path": evidence.file_path,
        "integrity_hash": evidence.integrity_hash,
        "format": evidence.format,
        "size_bytes": evidence.size_bytes,
        "original_bytes": len(raw),
        "metadata_stripped": True,
    }


def seed_demo_state(
    db: DBSession,
    *,
    embedder: Callable[[str], list[float]] | None = None,
) -> dict:
    if embedder is None:
        from app.services.embeddings import embed as embedder  # type: ignore

    user, mnemonic, session_token = _seed_whistleblower(db)
    baselines = _seed_baselines(db, user, embedder)
    evidence = _seed_evidence(db)
    db.commit()

    return {
        "whistleblower": {
            "national_id": WHISTLEBLOWER_NATIONAL_ID,
            "pseudonymous_token": user.pseudonymous_token,
            "recovery_mnemonic": mnemonic,
            "session_token": session_token,
            "reliability_index": user.reliability_index,
            "age_tier": user.age_tier,
            "points_total": user.points_total,
        },
        "baseline_reports": baselines,
        "evidence": evidence,
        "next_steps": [
            "POST /reports with Authorization: Bearer <session_token> to submit a follow-up report.",
            "POST /admin/assign with auditor_id=AUD-002 (clean COI for DEPT-CUSTOMS / DEPT-EDUCATION).",
            "POST /admin/verify with verdict=Verified to trigger RI bump and (Tier-4) protection order.",
            "GET  /public/stats to show the cached transparency dashboard refresh.",
            "GET  /wallet/rewards (Bearer auth) to show points + corruption-fighter badge progress.",
        ],
    }
