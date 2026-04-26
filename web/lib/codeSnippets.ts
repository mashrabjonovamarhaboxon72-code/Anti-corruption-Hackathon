/**
 * Backend code snippets shown in the WorkflowExplorer's "Technical
 * Deep-Dive" overlay. These are *real* excerpts from the corresponding
 * backend modules — not pseudocode — so what the demo presents is what
 * the system actually runs.
 *
 * Lengths are kept tight (12–22 lines) — enough to communicate the
 * concrete primitive without dropping a wall of code on the viewer.
 */

export interface CodeSnippet {
  /** Stable id matching the workflow step. */
  id: string;
  /** Repo path the excerpt was taken from. */
  source: string;
  /** Language tag for the highlighter + UI pill. */
  language: "python";
  /** The actual code body. */
  code: string;
  /** One-paragraph plain-English caption shown above the code. */
  caption: string;
}

export const SNIPPETS: Record<string, CodeSnippet> = {
  "anonymous-signup": {
    id: "anonymous-signup",
    source: "app/services/pseudonymous_token.py",
    language: "python",
    caption:
      "HMAC-SHA256 with a server-side salt. The national ID is normalized, then keyed-hashed — there is no inverse function from the resulting token back to the ID without stealing PT_SALT.",
    code: `import hashlib
import hmac

from app.config import PT_SALT


def generate_pseudonymous_token(national_id: str) -> str:
    if not isinstance(national_id, str) or not national_id.strip():
        raise ValueError("national_id must be a non-empty string")

    normalized = national_id.strip()
    return hmac.new(
        PT_SALT.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
`,
  },

  "recovery-phrase": {
    id: "recovery-phrase",
    source: "app/services/recovery.py",
    language: "python",
    caption:
      "BIP39 24-word phrase = 256 bits of entropy. The plaintext mnemonic is shown to the user once at registration; the server keeps only the salted HMAC. compare_digest gives constant-time verification against timing oracles.",
    code: `from mnemonic import Mnemonic

_mnemo = Mnemonic("english")
MNEMONIC_STRENGTH_BITS = 256  # 24 words

def generate_mnemonic() -> str:
    return _mnemo.generate(strength=MNEMONIC_STRENGTH_BITS)


def hash_mnemonic(mnemonic: str) -> str:
    return hmac.new(
        RECOVERY_SALT.encode("utf-8"),
        _normalize(mnemonic).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_mnemonic(mnemonic: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_mnemonic(mnemonic), stored_hash)
`,
  },

  "evidence-upload": {
    id: "evidence-upload",
    source: "app/services/image_sanitizer.py",
    language: "python",
    caption:
      "Allowlist sanitization: a fresh Image is created from raw pixels, so EXIF/GPS/XMP/ICC chunks cannot survive. The SHA-256 is computed in memory before the file is written, eliminating the TOCTOU window between save and hash.",
    code: `src = Image.open(BytesIO(file_bytes))
src.load()

# Reconstruct from raw pixels — metadata lives outside the pixel grid
# and cannot follow paste() into a new Image object.
cleansed = Image.new(mode, src.size)
cleansed.paste(src)

# Render to bytes first so file-on-disk and hash come from the SAME payload.
buf = BytesIO()
cleansed.save(buf, **save_kwargs)
payload = buf.getvalue()

sha256_hash = hashlib.sha256(payload).hexdigest()
dest.write_bytes(payload)

return SanitizedImage(
    path=dest,
    sha256_hash=sha256_hash,
    size_bytes=len(payload),
    format=fmt,
)
`,
  },

  "submit-report": {
    id: "submit-report",
    source: "app/services/duplicate_check.py",
    language: "python",
    caption:
      "Vector embedding via sentence-transformers/all-MiniLM-L6-v2 (~80 MB, fits the 512 MB free-tier RAM budget). Every existing report's embedding is loaded once; new reports are scored against all of them via cosine similarity. Above the threshold (default 0.88) the report is flagged Potential Duplicate.",
    code: `def check_for_duplicate(db: Session, text: str) -> DuplicateCheckResult:
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
`,
  },

  "auditor-review": {
    id: "auditor-review",
    source: "app/services/coi.py",
    language: "python",
    caption:
      "Two failure modes screened: same department, or a relative's name appearing verbatim in the report text. False positives (re-route an auditor) cost less than false negatives (a relative quietly auditing their own family) — substring matching favors caution.",
    code: `def evaluate_coi(auditor_id: str, report_text: str,
                 target_department_id: str | None) -> COIDecision:
    auditor = get_auditor(auditor_id)
    if auditor is None:
        return COIDecision(blocked=True, reason="UNKNOWN_AUDITOR", ...)

    auditor_dept = auditor.get("department_id")
    relatives = auditor.get("named_relatives", []) or []

    if target_department_id and auditor_dept == target_department_id:
        return COIDecision(blocked=True, reason="DEPARTMENT_MATCH", ...)

    haystack = report_text.lower()
    matched = [r for r in relatives if r and r.lower() in haystack]
    if matched:
        return COIDecision(blocked=True, reason="RELATIVE_MENTIONED",
                           matched_relatives=matched, ...)

    return COIDecision(blocked=False, reason=None, ...)
`,
  },

  "earn-points": {
    id: "earn-points",
    source: "app/services/scoring.py",
    language: "python",
    caption:
      "RI 0–1000 maps linearly to a 0×–2× multiplier centered at 1× (RI 500 = baseline new user). Every award appends a row to audit_ledger; ORM event listeners on the AuditLedger model raise on any update or delete attempt, simulating an immutable log at the application layer.",
    code: `CORRUPTION_TIERS: dict[int, int] = {
    1: 100, 2: 250, 3: 500, 4: 1000,
}


def _ri_multiplier(reliability_index: int) -> float:
    clamped = max(0, min(1000, reliability_index))
    return clamped / RI_BASELINE  # 500 -> 1.0x, 1000 -> 2.0x


def award_points(db, *, user, report_id, tier) -> PointAward:
    base = CORRUPTION_TIERS[tier]
    multiplier = _ri_multiplier(user.reliability_index)
    awarded = int(round(base * multiplier))

    user.points_total = (user.points_total or 0) + awarded
    db.add(AuditLedger(
        event_type="POINTS_AWARDED",
        user_id=user.id, report_id=report_id, tier=tier,
        base_points=base, ri_at_award=user.reliability_index,
        ri_multiplier=multiplier, awarded_points=awarded,
    ))
    db.commit()
`,
  },

  "redeem-privately": {
    id: "redeem-privately",
    source: "app/services/wallet.py",
    language: "python",
    caption:
      "self_destruct_transaction nulls the redeemer_pt and stamps a destruct timestamp the moment a voucher is used. The row survives for cohort-level fraud detection, but only an 8-character PT prefix is preserved in the audit ledger — far too few bits for re-identification.",
    code: `def self_destruct_transaction(db: Session, voucher: Voucher) -> Voucher:
    if voucher.status != "Used":
        raise ValueError("self_destruct only runs on vouchers in 'Used'.")

    severed_pt_prefix = (voucher.redeemer_pt or "")[:8]  # 32 bits

    voucher.redeemer_pt = None
    voucher.self_destructed_at = datetime.utcnow()

    db.add(AuditLedger(
        event_type="VOUCHER_USED",
        details={
            "voucher_code": voucher.code,
            "benefit_id": voucher.benefit_id,
            "points_cost": voucher.points_cost,
            "severed_pt_prefix": severed_pt_prefix,
        },
    ))
    db.commit()
    db.refresh(voucher)
    return voucher
`,
  },
};
