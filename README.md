# Integrity Shield

Anonymous corruption-reporting backend built with FastAPI.

## What it does

- **Pseudonymous identity** — citizens are identified by an HMAC-SHA256 token derived from their national ID and a server-side salt. The raw national ID is **never stored**.
- **Metadata sanitization** — image evidence is rebuilt from raw pixels, stripping all EXIF/GPS/XMP/ICC metadata before storage.
- **ML duplicate detection** — incoming reports are vectorized with `sentence-transformers/all-mpnet-base-v2` and compared via cosine similarity. Above the configured threshold (default `0.88`) → flagged `Potential Duplicate`, no points awarded.
- **Reputation-weighted scoring** — `points = tier_base × (RI / 500)` clamped 0×–2×. Tier bases: T1 100, T2 250, T3 500, T4 1000.
- **Conflict-of-Interest engine** — auditor assignments are screened against a mock National HR registry. Blocks on department match or relative mentioned in the report text.
- **Civic wallet with self-destruct vouchers** — citizens redeem points for tier-filtered benefits. Once a voucher is `Used`, the row's PT linkage is nulled so no operator can reverse-trace which citizen received which benefit.
- **Background RI recalculator** — auditor verdicts (`Verified` +50, `Malicious` −150) are folded into the user's RI by an asyncio loop. Future point awards automatically reflect the new RI.
- **Append-only audit ledger** — every award, COI block, RI change, and voucher use is appended to `audit_ledger`; updates and deletes raise at the ORM layer.

## Endpoints

| Method | Path                | Purpose                                                   |
| ------ | ------------------- | --------------------------------------------------------- |
| GET    | `/health`           | Liveness                                                  |
| POST   | `/auth/register`    | Issue a pseudonymous token from a national ID + age tier  |
| POST   | `/upload/evidence`  | Strip image metadata and store the file                   |
| POST   | `/reports`          | Submit a report; runs duplicate check + scoring           |
| POST   | `/admin/assign`     | Assign auditor to report (COI-screened)                   |
| POST   | `/admin/verify`     | Auditor marks report `Verified` or `Malicious`            |
| GET    | `/wallet/rewards`   | List benefits available for the user's age tier           |
| POST   | `/wallet/redeem`    | Spend points for a one-time voucher code                  |
| POST   | `/wallet/use`       | Mark voucher used → triggers self-destruct                |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env  # then edit PT_SALT to a long random secret
PT_SALT=$(openssl rand -hex 32) .venv/bin/uvicorn app.main:app --reload
```

`PT_SALT` is required — the app refuses to boot without it. Rotating it invalidates every existing pseudonymous token by design.

## Tests

```bash
PT_SALT=test-salt .venv/bin/python -m pytest tests/ -v
```

26 tests covering all seven phases. SQLite in-memory for ORM tests; embedding model is stubbed in unit tests so CI doesn't have to download ~420 MB.

## Mock data

- `app/mock_data/hr_registry.json` — auditor profiles (department, named relatives) for the COI engine. Replace with a live HR API call in production.

## Layout

```
app/
  main.py                  FastAPI app, lifespan, background loop
  background.py            asyncio scheduler (RI recalc every 30s)
  config.py                Env loading, salt enforcement
  database.py              SQLAlchemy engine, Base, session factory
  models/                  user, report, audit_ledger, assignment, voucher
  services/
    pseudonymous_token.py  HMAC-SHA256 PT generator
    image_sanitizer.py     EXIF-stripping image rewriter
    embeddings.py          Lazy-loaded sentence-transformer wrapper
    duplicate_check.py     Cosine-similarity scan
    scoring.py             Tier × RI multiplier; writes audit ledger
    coi.py                 Department + relative matcher
    hr_registry.py         JSON-mock HR lookup
    benefits_catalog.py    Static tier-keyed benefit list
    wallet.py              Voucher issue + self_destruct_transaction
    reliability.py         RI recalculation from verdicts
  routers/                 auth, upload, reports, admin, wallet
  mock_data/               hr_registry.json
tests/                     pytest suite (26 tests)
uploads/                   sanitized evidence files (gitignored)
```

## A note on schema migrations

`init_db` calls `Base.metadata.create_all`, which only **creates missing tables** — it does not add columns to existing ones. If you upgraded from v0.1.0, drop your local SQLite/Postgres DB before restarting, or wire up Alembic.
