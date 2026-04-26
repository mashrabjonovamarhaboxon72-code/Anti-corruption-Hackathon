from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evidence import Evidence
from app.services.image_sanitizer import sanitize_and_store

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_BYTES = 10 * 1024 * 1024


class UploadResponse(BaseModel):
    message: str
    evidence_id: int
    stored_path: str
    integrity_hash: str
    size_bytes: int
    metadata_stripped: bool


@router.post("/evidence", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    try:
        sanitized = sanitize_and_store(raw, file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}")

    evidence = Evidence(
        file_path=str(sanitized.path),
        integrity_hash=sanitized.sha256_hash,
        format=sanitized.format,
        size_bytes=sanitized.size_bytes,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return UploadResponse(
        message="Evidence cleansed and stored.",
        evidence_id=evidence.id,
        stored_path=evidence.file_path,
        integrity_hash=evidence.integrity_hash,
        size_bytes=evidence.size_bytes,
        metadata_stripped=True,
    )
