from fastapi import FastAPI

from app.database import init_db
from app.routers import auth, reports, upload

app = FastAPI(
    title="Integrity Shield",
    description=(
        "Anonymous corruption-reporting backend. Citizens are identified only "
        "by a pseudonymous HMAC token; raw national IDs are never stored. "
        "Image evidence is stripped of EXIF/GPS metadata before storage. "
        "Duplicate reports are detected via sentence-transformer embeddings. "
        "Points are awarded against an append-only audit ledger."
    ),
    version="0.1.0",
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(reports.router)
