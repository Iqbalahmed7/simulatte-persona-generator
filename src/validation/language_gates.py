"""src/validation/language_gates.py — CR-V multilingual validation gates.

Sprint 29 — Cursor
O15 BLOCKER ACTIVE: Language generation (Hindi, Tamil, Telugu, Marathi, Bengali,
Kannada, Gujarati) is NOT permitted until all CR-V gates pass and Tech Lead issues
written sign-off.

Gates:
    CR1-V  Isolation test         — 10-persona isolation run; all must pass
    CR2-V  Stereotype check       — 5-persona spot-check; ≥90% attribute-traceable, 0 prohibited scripts
    CR3-V  Human evaluator realism — ≥2 evaluators; mean score ≥4.0/5.0; no dim <3.0
    CR4-V  Bilingual fidelity     — ≥4/5 bilingual pairs confirmed same person

CR1-V and CR2-V always return GateStatus.NOT_RUN this sprint (O15 blocker active).
CR3-V and CR4-V implement evaluation logic but return EVIDENCE_NEEDED when no
evidence is submitted.

Usage:
    from src.validation.language_gates import (
        check_cr1_v, check_cr2_v, check_cr3_v, check_cr4_v,
        GateStatus, LanguageGateResult, O15_BLOCKER_REASON,
    )
    result = check_cr3_v("hindi", evidence={"evaluators": [...], "n_evaluators": 2})
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

class GateStatus(str, Enum):
    NOT_RUN = "NOT_RUN"                     # O15 blocker active — gate not yet run
    BLOCKED = "BLOCKED"                      # Prerequisite not met
    EVIDENCE_NEEDED = "EVIDENCE_NEEDED"      # Gate defined but no data submitted
    READY = "READY"                          # Gate passed
    FAILED = "FAILED"                        # Gate run and failed


# ---------------------------------------------------------------------------
# O15 blocker constant
# ---------------------------------------------------------------------------

O15_BLOCKER_REASON = (
    "O15 BLOCKER ACTIVE: Multilingual output requires per-language, per-region "
    "validation before it can be approved. Language generation code may not merge "
    "until all CR-V gates pass and Tech Lead issues written sign-off."
)


# ---------------------------------------------------------------------------
# Gate result dataclass
# ---------------------------------------------------------------------------

@dataclass
class LanguageGateResult:
    gate_id: str        # "CR1-V", "CR2-V", "CR3-V", "CR4-V"
    language: str       # e.g. "hindi", "tamil"
    status: GateStatus
    detail: str
    evidence: dict = field(default_factory=dict)  # submitted evidence; empty if not yet run


# ---------------------------------------------------------------------------
# CR1-V — Isolation gate
# ---------------------------------------------------------------------------

def check_cr1_v(language: str, evidence: dict | None = None) -> LanguageGateResult:
    """CR1-V: 10-persona isolation test.

    This sprint: always returns NOT_RUN with O15 blocker reason.

    When evidence is provided in a future sprint, it should check:
    - evidence["n_personas_tested"] >= 10
    - evidence["all_passed"] is True

    For now: return NOT_RUN regardless of evidence.
    """
    return LanguageGateResult(
        gate_id="CR1-V",
        language=language,
        status=GateStatus.NOT_RUN,
        detail=O15_BLOCKER_REASON,
        evidence={},
    )


# ---------------------------------------------------------------------------
# CR2-V — Stereotype gate
# ---------------------------------------------------------------------------

def check_cr2_v(language: str, evidence: dict | None = None) -> LanguageGateResult:
    """CR2-V: 5-persona spot-check.

    Pass threshold: >=90% of cultural details are attribute-traceable; 0 prohibited scripts.

    This sprint: always returns NOT_RUN with O15 blocker reason.
    """
    return LanguageGateResult(
        gate_id="CR2-V",
        language=language,
        status=GateStatus.NOT_RUN,
        detail=O15_BLOCKER_REASON,
        evidence={},
    )


# ---------------------------------------------------------------------------
# CR3-V — Human evaluator realism gate
# ---------------------------------------------------------------------------

def check_cr3_v(language: str, evidence: dict | None = None) -> LanguageGateResult:
    """CR3-V: >=2 human evaluators (native/near-native + domain knowledge);
    mean score >=4.0/5.0; no dimension <3.0.

    Evidence schema:
    {
        "evaluators": [
            {
                "name": str,
                "mean_score": float,
                "dimension_scores": [float, ...]
            },
            ...
        ],
        "n_evaluators": int
    }

    Gate READY when:
    - n_evaluators >= 2
    - mean of all evaluator mean_scores >= 4.0
    - no individual dimension_score < 3.0 across all evaluators

    Gate FAILED when the above conditions are not met (but evidence was submitted).
    Gate EVIDENCE_NEEDED when evidence is None or evaluators list is empty.
    """
    if evidence is None:
        return LanguageGateResult(
            gate_id="CR3-V",
            language=language,
            status=GateStatus.EVIDENCE_NEEDED,
            detail=(
                "No evidence submitted. Provide an evaluators list with at least "
                "2 native/near-native evaluators, each supplying mean_score and "
                "dimension_scores."
            ),
            evidence={},
        )

    evaluators: list = evidence.get("evaluators", [])

    if not evaluators:
        return LanguageGateResult(
            gate_id="CR3-V",
            language=language,
            status=GateStatus.EVIDENCE_NEEDED,
            detail=(
                "Evidence submitted but evaluators list is empty. "
                "At least 2 evaluators required."
            ),
            evidence=evidence,
        )

    n_evaluators: int = evidence.get("n_evaluators", len(evaluators))

    # Check minimum evaluator count
    if n_evaluators < 2:
        return LanguageGateResult(
            gate_id="CR3-V",
            language=language,
            status=GateStatus.FAILED,
            detail=(
                f"Insufficient evaluators: {n_evaluators} provided, minimum 2 required."
            ),
            evidence=evidence,
        )

    # Collect all mean scores
    mean_scores: list[float] = []
    for ev in evaluators:
        ms = ev.get("mean_score")
        if ms is not None:
            mean_scores.append(float(ms))

    # Check for any dimension score below 3.0
    low_dimension_failures: list[str] = []
    for ev in evaluators:
        dim_scores = ev.get("dimension_scores", [])
        for score in dim_scores:
            if float(score) < 3.0:
                evaluator_name = ev.get("name", "unknown")
                low_dimension_failures.append(
                    f"evaluator '{evaluator_name}' has dimension score {score:.2f} < 3.0"
                )

    # Compute overall mean of evaluator mean_scores
    if mean_scores:
        overall_mean = sum(mean_scores) / len(mean_scores)
    else:
        overall_mean = 0.0

    failures: list[str] = []

    if overall_mean < 4.0:
        failures.append(
            f"Overall mean score {overall_mean:.2f} < 4.0 required threshold."
        )

    failures.extend(low_dimension_failures)

    if failures:
        return LanguageGateResult(
            gate_id="CR3-V",
            language=language,
            status=GateStatus.FAILED,
            detail="CR3-V FAILED. " + " | ".join(failures),
            evidence=evidence,
        )

    return LanguageGateResult(
        gate_id="CR3-V",
        language=language,
        status=GateStatus.READY,
        detail=(
            f"CR3-V passed. {n_evaluators} evaluator(s); "
            f"overall mean score {overall_mean:.2f}/5.0; "
            "no dimension score below 3.0."
        ),
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# CR4-V — Bilingual fidelity gate
# ---------------------------------------------------------------------------

def check_cr4_v(language: str, evidence: dict | None = None) -> LanguageGateResult:
    """CR4-V: >=4/5 bilingual pairs confirmed same person.

    Evidence schema:
    {
        "pairs_tested": int,      # total pairs shown to evaluators
        "pairs_confirmed": int,   # pairs judged to be the same person
    }

    Gate READY when pairs_tested >= 5 AND pairs_confirmed >= 4.
    Gate FAILED when pairs_tested >= 5 AND pairs_confirmed < 4.
    Gate EVIDENCE_NEEDED when evidence is None or pairs_tested < 5.
    """
    if evidence is None:
        return LanguageGateResult(
            gate_id="CR4-V",
            language=language,
            status=GateStatus.EVIDENCE_NEEDED,
            detail=(
                "No evidence submitted. Provide pairs_tested (>=5) and "
                "pairs_confirmed to evaluate bilingual fidelity."
            ),
            evidence={},
        )

    pairs_tested: int = int(evidence.get("pairs_tested", 0))
    pairs_confirmed: int = int(evidence.get("pairs_confirmed", 0))

    if pairs_tested < 5:
        return LanguageGateResult(
            gate_id="CR4-V",
            language=language,
            status=GateStatus.EVIDENCE_NEEDED,
            detail=(
                f"Insufficient pairs tested: {pairs_tested} provided, "
                "minimum 5 required to evaluate this gate."
            ),
            evidence=evidence,
        )

    if pairs_confirmed >= 4:
        return LanguageGateResult(
            gate_id="CR4-V",
            language=language,
            status=GateStatus.READY,
            detail=(
                f"CR4-V passed. {pairs_confirmed}/{pairs_tested} bilingual pairs "
                "confirmed as same person (threshold: >=4/5)."
            ),
            evidence=evidence,
        )

    return LanguageGateResult(
        gate_id="CR4-V",
        language=language,
        status=GateStatus.FAILED,
        detail=(
            f"CR4-V FAILED. Only {pairs_confirmed}/{pairs_tested} bilingual pairs "
            "confirmed as same person. Threshold: >=4/5."
        ),
        evidence=evidence,
    )
