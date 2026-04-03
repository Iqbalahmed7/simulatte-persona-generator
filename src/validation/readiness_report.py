"""src/validation/readiness_report.py

Sprint 29 — O15 Language Readiness Report

Aggregates the four CR-V gate results into a single LanguageReadinessReport
with an overall status and a list of blocking reasons.

Status derivation rules:
    BLOCKED          — any gate has status NOT_RUN or BLOCKED
    EVIDENCE_NEEDED  — no gate is BLOCKED/NOT_RUN, but some are EVIDENCE_NEEDED
                       or FAILED
    READY_FOR_REVIEW — all four gates have status READY

Constitutional requirement:
    tech_lead_sign_off_required is ALWAYS True.  There is no code path that
    sets it to False.  This is an O15 framework mandate, not a configurable flag.

No LLM calls are made by this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.validation.language_gates import GateStatus, LanguageGateResult


# ---------------------------------------------------------------------------
# ReadinessStatus
# ---------------------------------------------------------------------------

class ReadinessStatus:
    BLOCKED = "BLOCKED"               # Any gate is NOT_RUN or BLOCKED
    EVIDENCE_NEEDED = "EVIDENCE_NEEDED"  # All gates defined but some need data
    READY_FOR_REVIEW = "READY_FOR_REVIEW"  # All four gates READY


# ---------------------------------------------------------------------------
# LanguageReadinessReport
# ---------------------------------------------------------------------------

@dataclass
class LanguageReadinessReport:
    """Aggregated language-readiness report for a single language.

    Attributes
    ----------
    language:
        The language identifier (e.g. "hindi", "tamil").
    status:
        One of the ReadinessStatus string constants.
    cr1_v_status … cr4_v_status:
        GateStatus value strings for each of the four CR-V gates.
    tech_lead_sign_off_required:
        Constitutional requirement — ALWAYS True.  No code path sets this False.
    blocking_reasons:
        Detail strings collected from any gate that is NOT_RUN, BLOCKED,
        EVIDENCE_NEEDED, or FAILED.
    notes:
        Free-text field for additional context.
    """

    language: str
    status: str                        # One of ReadinessStatus values
    cr1_v_status: str                  # GateStatus value string
    cr2_v_status: str
    cr3_v_status: str
    cr4_v_status: str
    # Constitutional requirement — always True; no code path sets this False.
    tech_lead_sign_off_required: bool
    blocking_reasons: list[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# _NON_READY_STATUSES — gates whose detail strings populate blocking_reasons
# ---------------------------------------------------------------------------

_NON_READY_STATUSES = {
    GateStatus.NOT_RUN,
    GateStatus.BLOCKED,
    GateStatus.EVIDENCE_NEEDED,
    GateStatus.FAILED,
}

_NOT_RUN_OR_BLOCKED = {GateStatus.NOT_RUN, GateStatus.BLOCKED}


# ---------------------------------------------------------------------------
# build_readiness_report
# ---------------------------------------------------------------------------

def build_readiness_report(
    language: str,
    cr1_result: LanguageGateResult,
    cr2_result: LanguageGateResult,
    cr3_result: LanguageGateResult,
    cr4_result: LanguageGateResult,
) -> LanguageReadinessReport:
    """Build a LanguageReadinessReport from four CR-V gate results.

    Status rules:
    - BLOCKED: any gate has status NOT_RUN or BLOCKED
    - EVIDENCE_NEEDED: no gate is BLOCKED/NOT_RUN, but some are EVIDENCE_NEEDED
      or FAILED
    - READY_FOR_REVIEW: all four gates have status READY

    tech_lead_sign_off_required is ALWAYS True — constitutional O15 requirement.

    Args:
        language:   Language identifier string (e.g. "hindi").
        cr1_result: LanguageGateResult for CR1-V.
        cr2_result: LanguageGateResult for CR2-V.
        cr3_result: LanguageGateResult for CR3-V.
        cr4_result: LanguageGateResult for CR4-V.

    Returns:
        LanguageReadinessReport with derived overall status and blocking reasons.
    """
    gate_results = [cr1_result, cr2_result, cr3_result, cr4_result]
    statuses = [r.status for r in gate_results]

    # --- Derive overall status -----------------------------------------------
    if any(s in _NOT_RUN_OR_BLOCKED for s in statuses):
        overall = ReadinessStatus.BLOCKED
    elif all(s == GateStatus.READY for s in statuses):
        overall = ReadinessStatus.READY_FOR_REVIEW
    else:
        overall = ReadinessStatus.EVIDENCE_NEEDED

    # --- Collect blocking reasons from any non-READY gate --------------------
    blocking_reasons: list[str] = [
        r.detail for r in gate_results if r.status in _NON_READY_STATUSES
    ]

    return LanguageReadinessReport(
        language=language,
        status=overall,
        cr1_v_status=cr1_result.status.value,
        cr2_v_status=cr2_result.status.value,
        cr3_v_status=cr3_result.status.value,
        cr4_v_status=cr4_result.status.value,
        # Constitutional requirement: always True — no code path sets this False.
        tech_lead_sign_off_required=True,
        blocking_reasons=blocking_reasons,
        notes="",
    )
