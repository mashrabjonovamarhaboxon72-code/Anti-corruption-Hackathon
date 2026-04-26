import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import background
from app.database import init_db
from app.routers import admin, auth, demo, public, reports, upload, wallet


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    background.start()
    try:
        yield
    finally:
        background.stop()


app = FastAPI(
    title="Integrity Shield",
    description=(
        "Anonymous corruption-reporting backend. Citizens are identified only "
        "by a pseudonymous HMAC token; raw national IDs are never stored. "
        "Image evidence is stripped of EXIF/GPS metadata before storage. "
        "Duplicate reports are detected via sentence-transformer embeddings. "
        "Auditor assignments are screened by a Conflict-of-Interest engine. "
        "Earned points redeem into self-destructing benefit vouchers. "
        "Reliability Index is recomputed in the background from auditor verdicts. "
        "Every state change is appended to an immutable audit ledger."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


# Single source of truth for the deployed frontend's origin. Set this to the
# Vercel URL (e.g. https://integrity-shield.vercel.app) once the frontend is
# live; defaults to http://localhost:3000 for local dev. A comma-separated
# value is accepted so an operator can authorize multiple origins (e.g. a
# preview deploy + production) without redeploying the backend.
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _frontend_url.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "Cache-Control"],
)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(wallet.router)
app.include_router(public.router)
app.include_router(demo.router)
