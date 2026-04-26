# Integrity Shield

A FastAPI backend for anonymous corruption reporting, built so that the operators of the system cannot identify the people who use it — even under subpoena, even on the night shift, even after a database breach.

This README is heavy on **why**. The architecture decisions below were made deliberately, often against easier alternatives, because the threat model includes both casual data leaks and motivated insiders.

---

## Table of contents

1. [Threat model](#threat-model)
2. [Security & privacy architecture](#security--privacy-architecture)
   - [Zero-knowledge identity (Pseudonymous Tokens)](#1-zero-knowledge-identity-pseudonymous-tokens)
   - [The Integrity Shield (evidence sanitization + hash anchoring)](#2-the-integrity-shield-evidence-sanitization--hash-anchoring)
   - [Self-destructing audit logs (reward severance)](#3-self-destructing-audit-logs-reward-severance)
   - [BIP39 recovery in a zero-knowledge system](#4-bip39-recovery-in-a-zero-knowledge-system)
   - [Two-layer caching for the public dashboard](#5-two-layer-caching-for-the-public-dashboard)
3. [What the system does](#what-the-system-does)
4. [API reference](#api-reference)
5. [Authentication flow](#authentication-flow)
6. [Setup](#setup)
7. [Demo mode](#demo-mode)
8. [Testing](#testing)
9. [Layout](#layout)
10. [Caveats and known gaps](#caveats-and-known-gaps)

---

## Threat model

| Adversary | What they can do | Whether we defend |
| --- | --- | --- |
| Database breach (SQL dump leaked) | Read every row of every table | **Yes** — no national IDs, no reward↔citizen links after redemption, no plaintext mnemonics, no EXIF/GPS in stored images |
| Curious operator with DB read access | Query for "who reported the customs office?" | **Yes** — the answer is a 64-char hex blob with no inverse function unless they also stole `PT_SALT` |
| Operator with DB *write* access | Tamper with `integrity_hash`, `recovery_hash`, audit_ledger via raw SQL | **Partial** — ORM-level immutability listeners block ledger updates from the application layer. Raw SQL bypasses them; defense is operational (least-privilege DB roles), not architectural |
| Filesystem attacker (modifies a stored evidence file) | Swap a damning photo for a benign one | **Yes** — re-hashing on every priority evaluation detects the change and revokes media-broadcast eligibility |
| Brute-forcer of `/auth/recover` | Probe national IDs and mnemonics | **Partial** — failure responses are byte-identical, timing is approximately constant, attempts are audit-logged. No rate limiter (operational gap) |
| Salt thief (stole `PT_SALT` only) | Recompute PTs from a guessed national ID | **Yes against a hash-only leak**, **no against a full secret + DB leak**. `PT_SALT` rotation is the kill switch and invalidates every existing token by design |
| Coercive subpoena ("tell us who redeemed voucher X") | Compel the operator to identify a redeemer | **Yes** — by the time the voucher is `Used`, the link is gone. The operator cannot answer because the data does not exist |
| Network attacker (TLS not in scope) | Sniff requests | **No** — terminate TLS at your reverse proxy, this is not an HTTPS server |

The system is built for operators who want to be able to truthfully tell a hostile actor: *"We can't help you, because we deliberately don't know."*

---

## Security & privacy architecture

### 1. Zero-knowledge identity (Pseudonymous Tokens)

> **Goal:** Identify a citizen for the lifetime of their account without ever recording their national ID. A leak of every database row should not enable re-identification of even a single citizen.

The system never stores a national ID. Instead, every place that would reference a citizen carries a **Pseudonymous Token (PT)** — a 64-character hex string that is deterministic per national ID but irreversible without the server-side secret.

#### Construction

```
PT = HMAC-SHA256(key = PT_SALT, message = normalize(national_id))
```

Implemented in `app/services/pseudonymous_token.py`.

#### Why HMAC-SHA256 instead of plain `SHA256(salt || national_id)`

- **Length-extension immunity.** SHA-256 is vulnerable to length-extension attacks; HMAC's two-stage construction is not. Even though national IDs are short (so practical length-extension is academic), the cost of HMAC is the same and the security property is strictly better.
- **Salt protection.** If an attacker steals only a dump of `pseudonymous_token` values, they cannot mount a precomputed dictionary attack against the national ID space without also stealing `PT_SALT`. Plain `SHA256(salt || id)` has the same property in theory, but HMAC's standardized derivation is well-analyzed and avoids subtle "what is the salt format?" mistakes.
- **No oracle from one PT to another.** Every input goes through the keyed compression independently. There is no shortcut from "I know one PT" to "I can guess another."

#### Salt separation: three independent secrets

The application refuses to start unless **all three** of these are set, and they must be different:

| Env var | Used for | What a leak enables |
| --- | --- | --- |
| `PT_SALT` | Hashing national IDs into PTs | Re-deriving PTs from guessed national IDs |
| `RECOVERY_SALT` | Hashing BIP39 mnemonics into `recovery_hash` | Brute-forcing the mnemonic word space |
| `PROTECTION_ORDER_SIGNING_KEY` | HMAC signing of Digital Protection Orders | Forging legally-relevant protection documents |

```python
PT_SALT = os.environ.get("PT_SALT")
if not PT_SALT:
    raise RuntimeError(
        "PT_SALT environment variable is required. "
        "Set it to a long random secret; rotating it invalidates all pseudonymous tokens."
    )
# ...similar guards for RECOVERY_SALT and PROTECTION_ORDER_SIGNING_KEY
```

The reason for **key separation** is failure isolation. If the same key were used for hashing PTs and signing protection orders, then a leak of either system would compromise both — and a developer who needs to rotate one would be forced to invalidate the other. With three keys, each can be rotated, audited, and stored separately (e.g., split across HSMs or KMS tenants in production).

#### Salt rotation is a deliberate kill switch

Rotating `PT_SALT` invalidates every existing PT in the database. This is a feature, not a bug:

- If `PT_SALT` is suspected to have leaked, rotating it makes the leaked rows useless: the new PTs do not match the old ones, so an attacker who recomputes PTs from guessed national IDs against the old salt finds no match in the new database.
- The trade-off is that **legitimate users also lose their accounts.** They must re-register. There is no mechanism to migrate PTs across salt rotations, because the entire point of the construction is that the server cannot reverse the old PT.

This is the price of zero-knowledge identity: the server is genuinely incapable of "fixing" things that depend on knowing who the citizen is.

---

### 2. The Integrity Shield (evidence sanitization + hash anchoring)

> **Goal:** Accept image evidence from citizens without (a) leaking their location via EXIF/GPS, (b) letting anyone substitute a different image for the original after the fact, or (c) letting a fabricated `evidence_path` count toward a report's trust score.

#### Stage 1: Metadata stripping by reconstruction

JPEGs and PNGs carry far more than pixels. EXIF tags can include the camera make/model, timestamps, GPS coordinates, the photographer's name, the device's serial number, and lens IDs. PNG ancillary chunks include ICC profiles and XMP metadata. WebP supports both.

Image editors usually offer a "remove metadata" option, but this is a blocklist approach — it strips the metadata it knows about and leaves anything it doesn't. We use an **allowlist** approach: only the pixel grid survives.

```python
# app/services/image_sanitizer.py
src = Image.open(BytesIO(file_bytes))
src.load()

# Reconstruct the image from raw pixels into a new Image object.
# EXIF, GPS, XMP, IPTC, ICC profile, and any other ancillary chunks live
# OUTSIDE the pixel grid — they cannot follow the pixels into a fresh Image.
cleansed = Image.new(mode, src.size)
cleansed.paste(src)
```

`Image.new()` creates an image with no metadata. `paste()` copies only the rasterized pixel values from source to destination. There is no metadata pipeline through which any field could survive — this is why the implementation is one line and why it cannot be defeated by a future EXIF tag the implementation has not heard of.

#### Stage 2: Hash anchoring

Stripping metadata at upload time is necessary but not sufficient. An attacker (or malicious operator) with filesystem access could replace the cleansed file with a tampered version after upload. We need to know whether the file on disk is still the same file we sanitized.

```python
# Render to bytes first so the on-disk file and the digest are computed
# from the exact same payload. Writing-then-reading would race against
# filesystem corruption.
buf = BytesIO()
cleansed.save(buf, **save_kwargs)
payload = buf.getvalue()
sha256_hash = hashlib.sha256(payload).hexdigest()
dest.write_bytes(payload)
```

The SHA-256 is computed on the **bytes that get written to disk**, in memory, before the write happens. This rules out a TOCTOU race where a concurrent writer modifies the file between save and hash. The hash is then persisted in the new `Evidence` table:

```sql
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR(512) UNIQUE NOT NULL,
    integrity_hash VARCHAR(64) NOT NULL,  -- SHA-256 hex of cleansed bytes
    format VARCHAR(8) NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

#### Stage 3: Re-verification at every decision point

The hash exists to be checked. The `ReportPriorityService` (which decides whether a report qualifies for the public media feed) re-hashes the file on disk every time it makes a priority decision:

```python
def verify_evidence_integrity(db, evidence_path):
    record = db.query(Evidence).filter(Evidence.file_path == evidence_path).one_or_none()
    if record is None:           # fabricated path, never uploaded
        return False
    current = hash_file(Path(evidence_path))
    if current is None:           # file was deleted
        return False
    return current == record.integrity_hash  # tampered? mismatch.
```

The +0.10 trust component for "evidence attached" is only awarded when this check passes. So:

| Scenario | trust_score result |
| --- | --- |
| Clean upload, file unchanged | full +0.10 |
| File modified after upload | -0.10, priority can be revoked |
| File deleted after upload | -0.10 |
| Fabricated `evidence_path` (no Evidence row) | -0.10 (no credit ever) |

`/admin/verify` re-runs the priority calculation on every verdict, so post-hoc tampering takes a report **off** the public media feed even after it's already shown up there.

#### What this does not protect against

Hash anchoring detects **filesystem-level** tampering. It does not detect **database-level** tampering — an attacker who can `UPDATE evidence SET integrity_hash = ...` can also forge the file. For real-world deployment, sign the digest at upload time with a server private key (Ed25519) so verification doesn't need to trust the database. The interface (`hash_file`, `verify_evidence_integrity`) doesn't change; only the comparison does.

---

### 3. Self-destructing audit logs (reward severance)

> **Goal:** When a citizen redeems points for a benefit voucher (transit subsidy, tax rebate, healthcare voucher), no record should survive that links *which citizen* received *which benefit*. Even the operator must not be able to answer this question after the redemption is complete.

This is a **cryptographic severance**, not just a UX choice. The whole point of paying citizens to report corruption is undermined if a corrupt official can later compel the operator to reveal "who got the bribe-reporter reward last month, and to which apartment." So the link is destroyed at the moment it's no longer needed.

#### Lifecycle of a voucher

```
                   ┌────────────────────────────────────────────┐
                   │  Voucher row in the DB                      │
                   │                                             │
   /wallet/redeem  │  status = "Issued"                          │
       points──►   │  redeemer_pt = <citizen's PT>  ◄── linked   │
                   │                                             │
                   └────────────────────────────────────────────┘
                                     │
                                     ▼
                   ┌────────────────────────────────────────────┐
                   │  /wallet/use (called by merchant)           │
                   │                                             │
                   │  status = "Used"                            │
                   │  used_at = NOW()                            │
                   │  redeemer_pt = <still set briefly>          │
                   │                                             │
                   └────────────────────────────────────────────┘
                                     │
                                     ▼
                   ┌────────────────────────────────────────────┐
                   │  self_destruct_transaction()                │
                   │                                             │
                   │  status = "Used"                            │
                   │  redeemer_pt = NULL  ◄── severed            │
                   │  self_destructed_at = NOW()                 │
                   │                                             │
                   └────────────────────────────────────────────┘
```

The implementation is intentionally simple:

```python
# app/services/wallet.py
def self_destruct_transaction(db, voucher):
    if voucher.status != "Used":
        raise ValueError("self_destruct only runs against vouchers in status 'Used'.")

    severed_pt_prefix = (voucher.redeemer_pt or "")[:8]  # 8 hex chars = 32 bits

    voucher.redeemer_pt = None
    voucher.self_destructed_at = datetime.utcnow()

    ledger = AuditLedger(
        event_type="VOUCHER_USED",
        details={
            "voucher_code": voucher.code,
            "benefit_id": voucher.benefit_id,
            "points_cost": voucher.points_cost,
            "severed_pt_prefix": severed_pt_prefix,  # NOT enough to re-identify
        },
    )
    db.add(ledger)
    db.commit()
```

#### Why the voucher row survives

We could `DELETE` the voucher row entirely, but then the system loses its ability to report aggregate metrics: "how many transit subsidies were redeemed this month?", "are merchants double-claiming vouchers?", etc. By keeping the row but nulling the PT field, we preserve **cohort-level analytics** while destroying **individual identifiability**.

#### The 8-character prefix

The audit ledger stores only an 8-hex-character prefix of the original PT (32 bits). This is:

- **Insufficient for re-identification.** A 32-bit space hashed across the citizen population yields collisions; you cannot point at one prefix and say "that is citizen X."
- **Sufficient for fraud detection.** If one prefix shows up redeeming 50 vouchers in a day, that's a pattern worth investigating. The prefix is the smallest signal that lets cohort-level fraud detection function.

This is a deliberate compromise: a tiny amount of correlation potential is preserved (could a determined attacker with prior PT knowledge confirm a single redemption? possibly) in exchange for operational ability to detect abuse. Adjust the prefix length, or remove it entirely, depending on your threat model.

#### What this does not protect against

The severance happens at `Used` time. Between `Issued` and `Used`, the link exists in the database. A live attacker watching the DB during that window can correlate. Mitigations:

- Keep voucher TTLs short (issue → use should be hours, not days).
- Encrypt `redeemer_pt` at rest with a key the application reads but the database engine doesn't.
- For highest-stakes deployments, treat unused vouchers as a privacy debt and run a sweep that auto-self-destructs vouchers older than N hours.

---

### 4. BIP39 recovery in a zero-knowledge system

> **Goal:** Let a citizen recover their account if they forget their session, without giving the server any ability to recover the account *for* them.

Traditional password resets require the server to know how to identify the user (so it can email a reset link). In a zero-knowledge system, the server doesn't have an email address, doesn't have a phone number, and doesn't have a name — it has only a PT, which is itself derived from a national ID the server never stored.

The only thing the server can do is **hold a hash that proves the user knew the right secret at registration time.** That secret is a 24-word BIP39 mnemonic.

#### Why BIP39, why 24 words

- **256 bits of entropy.** BIP39 24-word phrases encode 256 bits, of which 8 are checksum. That's 2^248 effectively-random outcomes — high enough that brute-force is computationally infeasible even with state-resourced attackers.
- **Standardized wordlist.** BIP39 uses a curated 2048-word English list with no two words sharing a 4-character prefix. Users can write the phrase down and read it back without ambiguity.
- **Built-in checksum.** The last 8 bits are a SHA-256 checksum of the entropy. A wrong word in transcription is detected before the server is even queried (`is_valid_mnemonic()` short-circuits invalid input).
- **Library maturity.** The `mnemonic` library has been used in cryptocurrency wallets for over a decade. Implementation bugs are well-known and patched.

#### Construction

```python
# app/services/recovery.py
def hash_mnemonic(mnemonic: str) -> str:
    return hmac.new(
        RECOVERY_SALT.encode("utf-8"),
        _normalize(mnemonic).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
```

The mnemonic is normalized (whitespace collapsed, lowercased) before hashing so cosmetic differences in transcription don't break recovery. The same normalization applies at write time and verify time.

#### The "shown once" property

```python
# app/routers/auth.py — register endpoint
mnemonic = generate_mnemonic()  # generates fresh
user = User(
    pseudonymous_token=pt,
    recovery_hash=hash_mnemonic(mnemonic),  # store only the hash
    ...
)
db.add(user); db.commit()
return RegisterResponse(
    ...
    recovery_mnemonic=mnemonic,  # cleartext — sent in this response only
)
```

The plaintext mnemonic appears exactly once: in the body of the registration response. It is never logged, never written to disk, never returned by any other endpoint. Re-registering the same `national_id` returns `created: false` and `recovery_mnemonic: null` — the server has no way to re-issue a mnemonic, because it doesn't know the original one.

This is intentional: if the server *could* re-issue, it would need to store the original somewhere, which would defeat the entire scheme.

#### Recovery flow

```python
# /auth/recover takes (national_id, mnemonic)
pt = generate_pseudonymous_token(national_id)        # factor 1: PT match
user = db.query(User).filter(...pt...).one_or_none()

# Even if user is None, run the verify against a dummy hash
# to keep timing roughly constant — don't leak "user exists" via timing.
target_hash = user.recovery_hash if (user and user.recovery_hash) else "0" * 64

if not is_valid_mnemonic(mnemonic) or not verify_mnemonic(mnemonic, target_hash):
    _audit_recovery(db, user_id=(user.id if user else None), success=False, ...)
    raise HTTPException(401, "Recovery failed.")  # generic message

# Mint session
session_token = secrets.token_urlsafe(32)
sess = SessionModel(session_token=session_token, pseudonymous_token=pt, expires_at=...)
```

#### Defenses baked in

| Attack | Defense |
| --- | --- |
| Probe whether a national ID is registered | Failure response is byte-identical for "no such ID" and "wrong mnemonic" — same status, same body, same headers |
| Time-side-channel ("user exists" is faster than "user missing") | Mnemonic check runs against a dummy hash even when the user doesn't exist |
| Timing variance in HMAC comparison | `hmac.compare_digest` does constant-time comparison |
| Submit garbage and watch for crashes | BIP39 checksum validation short-circuits non-conforming input cleanly to the same generic 401 |
| Brute-force mnemonics for one user | Every attempt — success or failure — is appended to `audit_ledger` as `AUTH_RECOVERY_SUCCESS` / `AUTH_RECOVERY_FAILED`, so patterns are visible to operators |

#### What this does not protect against

There is no rate limiter at the application layer. A determined attacker can submit attempts as fast as the network allows, and only the audit log records it. Production deployments must put a per-IP and per-PT rate limit in front of `/auth/recover`. Additionally, with 2^248 effective mnemonic space, no realistic rate of attempts threatens a single account — but rate limiting protects against denial-of-service against the audit pipeline.

---

### 5. Two-layer caching for the public dashboard

> **Goal:** Serve `/public/stats` to thousands of concurrent dashboard viewers during news cycles without ever overloading Postgres.

The transparency dashboard endpoint computes:

- Total Verified report count
- Aggregate civic impact (sum of tier across Verified reports)
- Per-department report breakdown
- Recent corruption-fighter badge earnings (no user IDs — just timestamps)

Each of these is a separate aggregate query. Run them on every request and a slashdot-effect spike turns into Postgres CPU at 100%.

#### Layer 1: In-process TTL cache with single-flight recompute

```python
# app/services/public_stats.py
class StatsCache:
    def __init__(self, ttl_seconds: int = PUBLIC_STATS_TTL_SECONDS):
        self._ttl = max(0, ttl_seconds)
        self._value: PublicStats | None = None
        self._expires_at: float = 0.0
        self._lock = Lock()

    def get(self, db: Session) -> PublicStats:
        now = time.monotonic()
        if self._value is not None and now < self._expires_at:
            return self._value                        # cheap path: object by identity
        with self._lock:
            now = time.monotonic()
            if self._value is None or now >= self._expires_at:
                self._value = compute_stats(db)       # one recompute per TTL
                self._expires_at = now + self._ttl
            return self._value
```

Two properties matter:

- **Identity reuse within the TTL window.** Every caller within the TTL gets the same Python object back, by identity. No serialization, no recompute, no DB hit.
- **Single-flight recompute.** The `Lock` and the **double-checked condition** inside the lock together guarantee that even if 1000 requests arrive simultaneously after expiry, only **one** of them runs `compute_stats(db)`. The other 999 wait briefly and read the cached result the winner just computed. This eliminates the thundering-herd pattern where everyone races to recompute.

#### Layer 2: HTTP `Cache-Control` for upstream CDN/proxy

```python
# app/routers/public.py
@router.get("/stats")
def public_stats(response: Response, db: Session = Depends(get_db)):
    stats = get_cache().get(db)
    response.headers["Cache-Control"] = f"public, max-age={PUBLIC_STATS_TTL_SECONDS}"
    return stats.to_dict()
```

A CDN (CloudFront, Fastly, Cloudflare) sitting in front of the app honors this header and serves cached responses to clients without ever touching the origin. With a 60-second TTL and an event that drives 10,000 viewers per second:

- Layer 2 (CDN) absorbs the bulk: ~10,000 req/sec → 1 req/min hits the app.
- Layer 1 (in-process) absorbs the rest: that 1 req/min hits the cache, not Postgres, except once per TTL window.

The two TTLs are deliberately the same so they expire in lockstep. If the CDN serves stale content for a few seconds past expiry, the next origin hit recomputes and refreshes both layers.

#### Why not skip Layer 1 and rely only on the CDN?

- Not all requests come from cacheable paths. Internal dashboards, monitoring, smoke tests, and admin operators may bypass the CDN — Layer 1 protects them too.
- CDN cache misses still happen (cold cache, edge node failover). When they do, Layer 1 is the only thing standing between the miss and the database.
- Local development and integration tests don't have a CDN. Layer 1 makes the cache behavior testable without standing up infrastructure.

#### Why not skip Layer 2 and rely only on Layer 1?

- Layer 1 is per-process. Horizontal scaling means N processes each running their own cache, each independently hitting the database every TTL. The CDN is shared across the world.
- TLS termination and connection handling at the app are not free either. Letting the CDN absorb 99% of requests reduces app CPU, network, and connection-pool pressure too.

#### Migration path

Both layers can be replaced with stronger primitives without changing the endpoint contract:

- Swap Layer 1 for Redis to share across replicas.
- Swap to a Postgres `MATERIALIZED VIEW` with `REFRESH MATERIALIZED VIEW CONCURRENTLY` if you need the cached state to outlive a process restart.
- Swap Layer 2 for an in-VPC reverse proxy if you can't use a public CDN.

The endpoint code does not change. The `Cache-Control` header is the contract.

---

## What the system does

In the order data flows:

1. **Citizen registers** → receives a PT, an RI of 500, and a 24-word recovery mnemonic (shown once).
2. **Citizen recovers** → presents national_id + mnemonic, receives a Bearer session token.
3. **Citizen uploads evidence** → image is rebuilt pixel-only, hashed, persisted as an `Evidence` row.
4. **Citizen submits report** with the evidence path and a Bearer token. The report is embedded with `sentence-transformers/all-mpnet-base-v2`, compared against existing reports for duplicates, scored for trust, awarded points (`tier_base × RI/500`), and possibly flagged `is_media_priority`.
5. **Auditor is assigned** via `/admin/assign`. The COI engine refuses on department match or relative-name substring hit in the report text.
6. **Auditor verifies** the report. `Verified` triggers a background RI bump (+50, capped at 1000) and may issue a Digital Protection Order (HMAC-signed JSON, Tier 4 + RI > 900). `Malicious` deducts 150 RI and revokes media priority.
7. **Citizen redeems points** → wallet issues a one-time voucher code.
8. **Merchant marks voucher used** → `self_destruct_transaction` severs the PT link.
9. **Public dashboard** at `/public/stats` aggregates totals, never touching identifiers.

Every transition is appended to an immutable `audit_ledger` whose `before_update` and `before_delete` ORM listeners raise.

---

## API reference

| Method | Path                  | Auth                    | Purpose                                                      |
| ------ | --------------------- | ----------------------- | ------------------------------------------------------------ |
| GET    | `/health`             | none                    | Liveness                                                     |
| POST   | `/auth/register`      | none                    | Issue PT + 24-word mnemonic (shown once)                     |
| POST   | `/auth/recover`       | none                    | (national_id + mnemonic) → session token                     |
| POST   | `/upload/evidence`    | none                    | Strip metadata, hash, persist Evidence row                   |
| POST   | `/reports`            | **Bearer**              | Submit report; runs duplicate check + scoring + priority     |
| POST   | `/admin/assign`       | none (mock auditor IDs) | COI-screened auditor assignment                              |
| POST   | `/admin/verify`       | none (mock auditor IDs) | Verdict; triggers RI delta + maybe protection order          |
| GET    | `/admin/media-feed`   | none (public)           | Tier 3+/trust>0.9 reports for transparency broadcasts        |
| POST   | `/admin/demo-setup`   | `DEMO_MODE=1`           | Wipes data, seeds Whistleblower + 3 baselines + 1 evidence   |
| GET    | `/wallet/rewards`     | **Bearer**              | List benefits for the user's age tier + earned badges        |
| POST   | `/wallet/redeem`      | **Bearer**              | Spend points → voucher code                                  |
| POST   | `/wallet/use`         | none (merchant-facing)  | Mark voucher used → self-destruct severs PT link             |
| GET    | `/public/stats`       | none (public)           | Cached aggregate dashboard metrics                           |

---

## Authentication flow

```
┌─────────────┐                                ┌──────────┐
│   Citizen   │                                │  Server  │
└──────┬──────┘                                └────┬─────┘
       │                                            │
       │ POST /auth/register {national_id}          │
       ├───────────────────────────────────────────►│
       │                                            │ Generate mnemonic
       │                                            │ Hash + store recovery_hash
       │                                            │ Compute PT = HMAC(salt, id)
       │ ◄──────────────────────────────────────────┤ Return {pt, mnemonic, ...}
       │                                            │
       │ (Citizen writes mnemonic on paper.)        │
       │                                            │
       │ POST /auth/recover {national_id, mnemonic} │
       ├───────────────────────────────────────────►│
       │                                            │ Recompute PT, look up user
       │                                            │ Verify mnemonic vs hash
       │                                            │ Mint Session row (24h TTL)
       │ ◄──────────────────────────────────────────┤ Return {pt, session_token, expires_at}
       │                                            │
       │ POST /reports                              │
       │ Authorization: Bearer <session_token>      │
       │ {text, tier, evidence_path, ...}           │
       ├───────────────────────────────────────────►│
       │                                            │ get_current_pt():
       │                                            │   parse Bearer, lookup Session,
       │                                            │   verify not expired/revoked,
       │                                            │   return session.pseudonymous_token
       │                                            │ ↓
       │                                            │ Submit logic uses returned PT
       │ ◄──────────────────────────────────────────┤ 201 Created
```

---

## Setup

### Required environment variables

```bash
PT_SALT=$(openssl rand -hex 32)
RECOVERY_SALT=$(openssl rand -hex 32)
PROTECTION_ORDER_SIGNING_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql+psycopg2://...   # or sqlite:///./local.db for dev
```

All three secrets are **required** at startup. The application refuses to boot if any is missing. They must be different from each other (key separation).

### Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env             # then edit
.venv/bin/uvicorn app.main:app --reload
```

The first time you submit a report, the duplicate-check service lazy-loads `sentence-transformers/all-mpnet-base-v2` (~420 MB). To pre-warm:

```bash
.venv/bin/python -c "from app.services.embeddings import embed; embed('warmup')"
```

---

## Demo mode

`/admin/demo-setup` is a destructive endpoint that wipes the data plane and seeds a known state for live demonstrations. It is gated by the `DEMO_MODE` env var and refuses to run unless explicitly enabled.

```bash
DEMO_MODE=1 .venv/bin/uvicorn app.main:app --reload

# In another terminal:
curl -X POST http://localhost:8000/admin/demo-setup | jq
```

The response includes the Whistleblower's PT, recovery mnemonic, and a ready-to-use session token, plus three baseline reports and a sanitized demo evidence file. **Never set `DEMO_MODE=1` in production.**

---

## Testing

```bash
.venv/bin/python -m pytest tests/ -v
```

92 tests. SQLite in-memory for ORM tests; the embedding model is stubbed so CI does not download 420 MB. Endpoint tests use `TestClient` with a `StaticPool` so the in-memory DB is shared across the app's worker thread.

---

## Layout

```
app/
  main.py                  FastAPI app, lifespan, background loop
  background.py            asyncio scheduler (RI recalc every 30s)
  config.py                Env loading, three-secret enforcement, DEMO_MODE
  database.py              SQLAlchemy engine, Base, session factory
  models/
    user.py                PT, RI, age_tier, recovery_hash
    report.py              text, tier, embedding, trust_score, is_media_priority
    evidence.py            file_path UNIQUE, integrity_hash
    voucher.py             code, redeemer_pt (NULLed on self-destruct)
    session.py             Bearer session row with TTL
    audit_ledger.py        Append-only; ORM update/delete listeners raise
    assignment.py          Auditor → report
    protection_order.py    HMAC-signed Digital Protection Order
  services/
    pseudonymous_token.py  HMAC-SHA256 PT generator
    image_sanitizer.py     EXIF-stripping image rewriter + hash_file()
    evidence_integrity.py  verify_evidence_integrity()
    embeddings.py          Lazy-loaded sentence-transformer wrapper
    duplicate_check.py     Cosine-similarity scan
    scoring.py             Tier × RI multiplier; writes audit ledger
    coi.py                 Department + relative matcher
    hr_registry.py         JSON-mock HR lookup
    benefits_catalog.py    Static tier-keyed benefit list
    wallet.py              Voucher issue + self_destruct_transaction
    reliability.py         RI recalculation from verdicts
    priority.py            ReportPriorityService — trust formula
    protection_order.py    sign_payload, verify_signature, maybe_issue
    badges.py              Corruption-fighter badge derivation
    recovery.py            BIP39 mnemonic generation + verify
    public_stats.py        compute_stats + StatsCache (in-process TTL)
    demo_seed.py           reset_database + seed_demo_state
  routers/
    auth.py                /auth/register, /auth/recover
    upload.py              /upload/evidence
    reports.py             /reports
    admin.py               /admin/assign, /admin/verify, /admin/media-feed
    wallet.py              /wallet/rewards, /wallet/redeem, /wallet/use
    public.py              /public/stats
    demo.py                /admin/demo-setup (DEMO_MODE-gated)
    deps.py                get_current_pt — Bearer session dependency
  mock_data/
    hr_registry.json       Auditor profiles for COI engine
tests/                     92 tests
uploads/                   sanitized evidence files (gitignored)
```

---

## Caveats and known gaps

These are deliberately open. Implementing them is straightforward — the architecture is designed to accommodate them — but they are out of scope for the current iteration:

| Gap | Why it matters | Mitigation |
| --- | --- | --- |
| No rate limiter on `/auth/recover` | A determined attacker can hammer recovery attempts | Front with a per-IP and per-PT-prefix rate limit (e.g., nginx `limit_req`) |
| No real auditor authentication | `/admin/assign` and `/admin/verify` trust the `auditor_id` in the request body | Add a separate auditor session domain, distinct from citizen sessions |
| Schema migrations are manual | `init_db` only creates missing tables; column additions need a DB drop or Alembic | Wire Alembic when the schema stabilizes |
| Single-replica caching | The in-process `StatsCache` doesn't share across processes | Promote to Redis or a real materialized view if traffic warrants |
| HMAC, not asymmetric, for protection orders | Anyone with `PROTECTION_ORDER_SIGNING_KEY` can forge orders | Swap to Ed25519 for cross-org legal use |
| No TLS termination | This is an app server, not an HTTPS server | Terminate at your reverse proxy/CDN |
| Session token rotation absent | Compromised sessions live for 24 h | Add a `/auth/logout` and a per-PT session-revocation sweep |
| `/wallet/use` has no merchant auth | Anyone with a voucher code can mark it used | Real merchant integration needs its own auth domain |

---

## License

See `LICENSE` (TODO).
