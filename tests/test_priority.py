import os
import sys
from pathlib import Path

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.priority import (
    PRIORITY_TRUST_THRESHOLD,
    compute_trust_score,
    evaluate_priority,
)


def test_max_signals_score_is_one():
    s = compute_trust_score(reliability_index=1000, similarity=0.0, evidence_verified=True, has_target_department=True)
    assert s == 1.0


def test_min_signals_score_is_zero():
    s = compute_trust_score(reliability_index=0, similarity=1.0, evidence_verified=False, has_target_department=False)
    assert s == 0.0


def test_baseline_user_no_extras_below_priority_cutoff():
    # RI 500, no duplicate, no evidence, no target dept -> 0.25 + 0.30 = 0.55
    s = compute_trust_score(reliability_index=500, similarity=0.0, evidence_verified=False, has_target_department=False)
    assert abs(s - 0.55) < 1e-6
    assert s <= PRIORITY_TRUST_THRESHOLD


def test_tier_3_with_high_trust_qualifies():
    d = evaluate_priority(
        tier=3,
        reliability_index=950,
        similarity=0.0,
        evidence_verified=True,
        has_target_department=True,
    )
    assert d.is_media_priority is True
    assert d.trust_score > PRIORITY_TRUST_THRESHOLD


def test_tier_2_never_qualifies_even_at_max_trust():
    d = evaluate_priority(
        tier=2,
        reliability_index=1000,
        similarity=0.0,
        evidence_verified=True,
        has_target_department=True,
    )
    assert d.is_media_priority is False
    assert d.trust_score == 1.0


def test_high_similarity_drops_below_cutoff():
    # similarity 0.95 strips the novelty contribution to ~0.015
    d = evaluate_priority(
        tier=4,
        reliability_index=1000,
        similarity=0.95,
        evidence_verified=True,
        has_target_department=True,
    )
    assert d.is_media_priority is False


def test_malicious_verdict_revokes_priority_even_when_qualified():
    d = evaluate_priority(
        tier=4,
        reliability_index=1000,
        similarity=0.0,
        evidence_verified=True,
        has_target_department=True,
        verification_status="Malicious",
    )
    assert d.is_media_priority is False
    assert "verdict_malicious_revokes_priority" in d.reasons


def test_threshold_is_strictly_greater_than():
    # exactly at 0.9 must NOT qualify
    d = evaluate_priority(
        tier=3,
        reliability_index=600,  # 0.30
        similarity=0.0,         # +0.30
        evidence_verified=True,      # +0.10
        has_target_department=True,  # +0.10
    )
    # 0.30 + 0.30 + 0.10 + 0.10 = 0.80, not at the boundary; let's use boundary case:
    boundary = compute_trust_score(reliability_index=1000, similarity=0.333, evidence_verified=True, has_target_department=True)
    # 0.50 + 0.30*0.667 + 0.10 + 0.10 = ~0.9001 — round to 0.9001
    # Force a true 0.9 case:
    exact = compute_trust_score(reliability_index=1000, similarity=1.0/3.0, evidence_verified=True, has_target_department=True)
    # equals 0.5 + 0.2 + 0.1 + 0.1 = 0.9
    assert exact == 0.9
    d2 = evaluate_priority(
        tier=4,
        reliability_index=1000,
        similarity=1.0/3.0,
        evidence_verified=True,
        has_target_department=True,
    )
    assert d2.is_media_priority is False  # > 0.9, not >= 0.9
