from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services.image_sanitizer import sanitize_and_store

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_BYTES = 10 * 1024 * 1024


@router.post("/evidence", status_code=status.HTTP_201_CREATED)
async def upload_evidence(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    try:
        stored = sanitize_and_store(raw, file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}")

    return {
        "message": "Evidence cleansed and stored.",
        "stored_path": str(stored),
        "metadata_stripped": True,
    }
