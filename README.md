# Integrity Shield

Anonymous corruption-reporting backend built with FastAPI.

## What it does

- **Pseudonymous identity** — citizens are identified by an HMAC-SHA256 token derived from their national ID and a server-side salt. The raw national ID is **never stored**.
- **Metadata sanitization** — image evidence is rebuilt from raw pixels, stripping all EXIF/GPS/XMP/ICC metadata before storage.
- **Duplicate detection** — incoming reports are vectorized with `sentence-transformers/all-mpnet-base-v2` and compared via cosine similarity against existing reports. Anything above the configured threshold (default `0.88`) is flagged `Potential Duplicate`.
- **Reputation-weighted scoring** — points = `tier_base × (RI / 500)` clamped to 0×–2×. Tier bases: T1 100, T2 250, T3 500, T4 1000.
- **Append-only audit ledger** — every award is written to `audit_ledger`; updates and deletes raise at the ORM layer.

## Endpoints

| Method | Path                | Purpose                                     |
| ------ | ------------------- | ------------------------------------------- |
| POST   | `/auth/register`    | Issue a pseudonymous token from a national ID |
| POST   | `/upload/evidence`  | Strip image metadata and store the file     |
| POST   | `/reports`          | Submit a report; runs duplicate check + scoring |
| GET    | `/health`           | Liveness                                    |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env  # then edit PT_SALT to a long random secret
.venv/bin/uvicorn app.main:app --reload
```

`PT_SALT` is required — the app refuses to boot without it. Rotating it invalidates every existing pseudonymous token by design.

## Tests

```bash
PT_SALT=test-salt .venv/bin/python -m pytest tests/ -v
```

Scoring and duplicate-check tests run against in-memory SQLite. The duplicate-check unit tests stub the embedding model so CI doesn't have to download ~420 MB.

## Layout

```
app/
  main.py              FastAPI app, startup hook
  config.py            Env loading, salt enforcement
  database.py          SQLAlchemy engine, Base, session factory
  models/              user, report, audit_ledger
  services/            pseudonymous_token, image_sanitizer, embeddings,
                       duplicate_check, scoring
  routers/             auth, upload, reports
tests/                 pytest suite (13 tests)
uploads/               sanitized evidence files (gitignored)
```
