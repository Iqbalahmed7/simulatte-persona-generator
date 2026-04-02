"""src/modalities/survey.py — One-time survey modality runner.

Sprint 6 — Codex (Survey Runner)

Spec: §1 (one-time survey modality), §9 (cognitive loop — decide)
Validity Protocol: BV4, BV5

One-time survey: core memory only; working memory is empty at start and
discarded after each run. Personas run concurrently per question.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from uuid import uuid4

from src.cognition.decide import decide, DecisionOutput
from src.experiment.modality import reset_working_memory
from src.schema.persona import PersonaRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SurveyQuestion:
    id: str
    text: str                              # the question as presented to the persona
    category: str = "general"             # e.g. "brand_perception", "purchase_intent"


@dataclass
class PersonaResponse:
    persona_id: str
    persona_name: str
    question_id: str
    decision: str                          # DecisionOutput.decision
    confidence: int                        # DecisionOutput.confidence
    key_drivers: list[str]                 # DecisionOutput.key_drivers
    reasoning_trace: str                   # DecisionOutput.reasoning_trace
    objections: list[str]                  # DecisionOutput.objections


@dataclass
class SurveyResult:
    survey_id: str
    questions: list[SurveyQuestion]
    responses: list[PersonaResponse]       # one per persona × question
    modality: str = "one_time_survey"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _answer_question(
    q: SurveyQuestion,
    persona: PersonaRecord,
) -> PersonaResponse:
    """Call decide() for a single persona/question pair.

    Passes empty memories list — one-time survey modality does not use
    prior working memory experiences.
    """
    output: DecisionOutput = await decide(
        scenario=q.text,
        memories=[],          # BV4/BV5: no working memory for one-time survey
        persona=persona,
    )
    return PersonaResponse(
        persona_id=persona.persona_id,
        persona_name=persona.demographic_anchor.name,
        question_id=q.id,
        decision=output.decision,
        confidence=output.confidence,
        key_drivers=output.key_drivers,
        reasoning_trace=output.reasoning_trace,
        objections=output.objections,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def run_survey(
    questions: list[SurveyQuestion],
    personas: list[PersonaRecord],
    survey_id: str | None = None,
) -> SurveyResult:
    """Run a one-time survey across all personas.

    For each persona:
    1. Reset working memory (core only — one-time survey modality).
    2. For each question: call decide(question.text, [], persona)
       — pass empty memories list (no prior working memory).
    3. Collect PersonaResponse for each question.

    survey_id defaults to f"survey-{uuid4().hex[:8]}".
    All decide() calls are awaited. Questions per persona run sequentially.
    Personas run concurrently via asyncio.gather() per question.
    """
    if survey_id is None:
        survey_id = f"survey-{uuid4().hex[:8]}"

    # Reset working memory for every persona once before the survey begins.
    # Core memory is preserved; working memory starts empty (one-time modality rule).
    reset_personas = [reset_working_memory(p) for p in personas]

    all_responses: list[PersonaResponse] = []

    # Run one asyncio.gather() per question — all personas answer each question
    # concurrently, then move to the next question in sequence.
    for question in questions:
        logger.debug(
            "run_survey: gathering responses for question %s across %d persona(s)",
            question.id,
            len(reset_personas),
        )
        tasks = [_answer_question(q=question, persona=p) for p in reset_personas]
        question_responses: tuple[PersonaResponse, ...] = await asyncio.gather(*tasks)
        all_responses.extend(question_responses)

    return SurveyResult(
        survey_id=survey_id,
        questions=questions,
        responses=all_responses,
    )
