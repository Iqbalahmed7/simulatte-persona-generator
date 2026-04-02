"""src/modalities/survey_report.py — Survey report formatter.

Sprint 6 — Codex (Survey Report)

Spec: §1 (one-time survey modality)
Validity Protocol: BV4, BV5

Pure-computation report generation — no LLM calls.
Produces per-persona responses and cohort-level summaries from a SurveyResult.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from src.modalities.survey import PersonaResponse, SurveyResult


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class QuestionSummary:
    question_id: str
    question_text: str
    decision_distribution: dict[str, int]   # normalised decision → count
    avg_confidence: float
    top_shared_drivers: list[str]           # drivers appearing in >=2 personas
    divergence_flag: bool                   # True if no decision accounts for >50%


@dataclass
class SurveyReport:
    survey_id: str
    cohort_size: int
    question_summaries: list[QuestionSummary]
    per_persona_responses: dict[str, list[PersonaResponse]]  # persona_id → responses


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_decision(text: str) -> str:
    """Normalise a decision string to a short canonical key.

    yes/no prefix matching; otherwise first 40 chars of lowercased text.
    """
    t = text.lower().strip()
    if t.startswith("yes"):
        return "yes"
    if t.startswith("no"):
        return "no"
    return t[:40]


def _build_question_summary(
    question_id: str,
    question_text: str,
    responses: list[PersonaResponse],
) -> QuestionSummary:
    """Compute aggregated statistics for a single question."""
    # Decision distribution
    decision_distribution: dict[str, int] = Counter(
        _normalize_decision(r.decision) for r in responses
    )

    # Average confidence
    if responses:
        avg_confidence = sum(r.confidence for r in responses) / len(responses)
    else:
        avg_confidence = 0.0

    # Top shared drivers — drivers appearing in >=2 distinct persona responses
    # Each response is already from one persona; count distinct persona_ids per driver.
    driver_to_personas: dict[str, set[str]] = defaultdict(set)
    for r in responses:
        for driver in r.key_drivers:
            driver_to_personas[driver].add(r.persona_id)

    top_shared_drivers = [
        driver
        for driver, personas in driver_to_personas.items()
        if len(personas) >= 2
    ]

    # Divergence flag: True if no single normalised decision accounts for >50%
    total = len(responses)
    if total == 0:
        divergence_flag = False
    else:
        max_count = max(decision_distribution.values(), default=0)
        divergence_flag = (max_count / total) <= 0.5

    return QuestionSummary(
        question_id=question_id,
        question_text=question_text,
        decision_distribution=dict(decision_distribution),
        avg_confidence=avg_confidence,
        top_shared_drivers=top_shared_drivers,
        divergence_flag=divergence_flag,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def generate_report(result: SurveyResult) -> SurveyReport:
    """Produce a structured SurveyReport from a SurveyResult.

    All computation is deterministic — no LLM calls.

    Steps:
    1. Build per_persona_responses index (persona_id → list[PersonaResponse]).
    2. For each question, collect its responses and build a QuestionSummary
       (decision distribution, avg confidence, shared drivers, divergence flag).
    3. Return SurveyReport with cohort_size = number of distinct personas.
    """
    # Index responses by persona_id
    per_persona: dict[str, list[PersonaResponse]] = defaultdict(list)
    for response in result.responses:
        per_persona[response.persona_id].append(response)

    cohort_size = len(per_persona)

    # Build a lookup: question_id → text (from result.questions)
    question_text_map: dict[str, str] = {q.id: q.text for q in result.questions}

    # Index responses by question_id
    per_question: dict[str, list[PersonaResponse]] = defaultdict(list)
    for response in result.responses:
        per_question[response.question_id].append(response)

    # Build QuestionSummary for each question, preserving original order
    question_summaries: list[QuestionSummary] = []
    for question in result.questions:
        qid = question.id
        qtext = question_text_map.get(qid, "")
        responses_for_q = per_question.get(qid, [])
        summary = _build_question_summary(qid, qtext, responses_for_q)
        question_summaries.append(summary)

    return SurveyReport(
        survey_id=result.survey_id,
        cohort_size=cohort_size,
        question_summaries=question_summaries,
        per_persona_responses=dict(per_persona),
    )
