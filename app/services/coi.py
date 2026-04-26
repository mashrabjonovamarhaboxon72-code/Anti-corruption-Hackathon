"""Conflict-of-Interest engine.

Two failure modes are checked:
  1. Departmental — auditor works for the department being investigated.
  2. Familial    — a named relative of the auditor appears verbatim in the
                   report description.

Matching is case-insensitive but uses substring search rather than tokenized
NER. That's intentional for a hackathon: the false-positive cost (a blocked
assignment requiring re-routing) is far lower than the false-negative cost
(a relative quietly auditing their own family). Tighten with NER later.
"""

from dataclasses import dataclass

from app.services.hr_registry import get_auditor


@dataclass
class COIDecision:
    blocked: bool
    reason: str | None
    matched_relatives: list[str]
    auditor_department: str | None
    target_department: str | None


def evaluate_coi(auditor_id: str, report_text: str, target_department_id: str | None) -> COIDecision:
    auditor = get_auditor(auditor_id)
    if auditor is None:
        return COIDecision(
            blocked=True,
            reason="UNKNOWN_AUDITOR",
            matched_relatives=[],
            auditor_department=None,
            target_department=target_department_id,
        )

    auditor_dept = auditor.get("department_id")
    relatives = auditor.get("named_relatives", []) or []

    if target_department_id and auditor_dept and auditor_dept == target_department_id:
        return COIDecision(
            blocked=True,
            reason="DEPARTMENT_MATCH",
            matched_relatives=[],
            auditor_department=auditor_dept,
            target_department=target_department_id,
        )

    haystack = report_text.lower()
    matched = [r for r in relatives if r and r.lower() in haystack]
    if matched:
        return COIDecision(
            blocked=True,
            reason="RELATIVE_MENTIONED",
            matched_relatives=matched,
            auditor_department=auditor_dept,
            target_department=target_department_id,
        )

    return COIDecision(
        blocked=False,
        reason=None,
        matched_relatives=[],
        auditor_department=auditor_dept,
        target_department=target_department_id,
    )
