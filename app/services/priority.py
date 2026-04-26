"""ReportPriorityService.

Decides whether a report belongs in the public-facing media feed.

`trust_score` is a deterministic composite in [0.0, 1.0] computed from
signals available at submission time:

  0.50 × (reporter RI / 1000)   reporter reputation (baseline up to 0.50)
+ 0.30 × (1 − similarity)       novelty — penalizes near-duplicates
+ 0.10 if evidence_verified     attached file's current hash matches the
                                integrity_hash captured at sanitization
+ 0.10 if target_department_id  clear accountability target

A high-RI reporter (RI≈1000) with no duplicate match, an attached evidence
file, and a named target department lands at 1.0. The 0.9 priority cut-off
therefore requires *most* signals to be strong simultaneously — it is not
something a single-axis maxed value can clear on its own.

Media priority = (tier ∈ {3, 4}) ∧ (trust_score > 0.9). A `Malicious`
verdict from an auditor unconditionally revokes priority.
"""

from dataclasses import dataclass

PRIORITY_TIERS = {3, 4}
PRIORITY_TRUST_THRESHOLD = 0.9


@dataclass
class PriorityDecision:
    trust_score: float
    is_media_priority: bool
    reasons: list[str]


def compute_trust_score(
    *,
    reliability_index: int,
    similarity: float | None,
    evidence_verified: bool,
    has_target_department: bool,
) -> float:
    ri_component = 0.5 * max(0, min(1000, reliability_index)) / 1000
    sim = 0.0 if similarity is None else max(0.0, min(1.0, similarity))
    novelty_component = 0.3 * (1.0 - sim)
    evidence_component = 0.1 if evidence_verified else 0.0
    target_component = 0.1 if has_target_department else 0.0
    score = ri_component + novelty_component + evidence_component + target_component
    return round(max(0.0, min(1.0, score)), 4)


def evaluate_priority(
    *,
    tier: int,
    reliability_index: int,
    similarity: float | None,
    evidence_verified: bool,
    has_target_department: bool,
    verification_status: str | None = None,
) -> PriorityDecision:
    score = compute_trust_score(
        reliability_index=reliability_index,
        similarity=similarity,
        evidence_verified=evidence_verified,
        has_target_department=has_target_department,
    )

    reasons: list[str] = []

    if verification_status == "Malicious":
        reasons.append("verdict_malicious_revokes_priority")
        return PriorityDecision(trust_score=score, is_media_priority=False, reasons=reasons)

    if tier not in PRIORITY_TIERS:
        reasons.append(f"tier_{tier}_below_priority_threshold")
        return PriorityDecision(trust_score=score, is_media_priority=False, reasons=reasons)

    if score <= PRIORITY_TRUST_THRESHOLD:
        reasons.append(f"trust_{score}_at_or_below_{PRIORITY_TRUST_THRESHOLD}")
        return PriorityDecision(trust_score=score, is_media_priority=False, reasons=reasons)

    reasons.append("tier_and_trust_qualify")
    if verification_status == "Verified":
        reasons.append("verdict_verified")
    return PriorityDecision(trust_score=score, is_media_priority=True, reasons=reasons)
