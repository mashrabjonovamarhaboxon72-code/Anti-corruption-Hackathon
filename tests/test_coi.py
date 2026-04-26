import os
import sys
from pathlib import Path

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.coi import evaluate_coi


def test_unknown_auditor_blocks():
    d = evaluate_coi("AUD-NONEXISTENT", "some report", "DEPT-CUSTOMS")
    assert d.blocked
    assert d.reason == "UNKNOWN_AUDITOR"


def test_department_match_blocks():
    d = evaluate_coi("AUD-001", "alleged smuggling at the border", "DEPT-CUSTOMS")
    assert d.blocked
    assert d.reason == "DEPARTMENT_MATCH"


def test_relative_in_text_blocks_case_insensitive():
    d = evaluate_coi(
        "AUD-001",
        "Officer DILSHOD KARIMOV demanded a bribe at terminal 3.",
        "DEPT-TRAFFIC-POLICE",
    )
    assert d.blocked
    assert d.reason == "RELATIVE_MENTIONED"
    assert "Dilshod Karimov" in d.matched_relatives


def test_clean_assignment_passes():
    d = evaluate_coi(
        "AUD-003",
        "Customs official asked for unrecorded cash payment.",
        "DEPT-CUSTOMS",
    )
    assert not d.blocked
    assert d.auditor_department == "DEPT-TAX"


def test_no_target_department_skips_dept_check():
    d = evaluate_coi("AUD-003", "generic complaint", None)
    assert not d.blocked
