"""src/experiment/session.py — Experiment session factory.

Ties a persona (or cohort), a modality, and a stimulus sequence into an
experiment session. Resets working memory before handing the session back
to the caller so each experiment starts from a clean slate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from src.schema.cohort import CohortEnvelope
from src.schema.persona import PersonaRecord
from src.experiment.modality import ExperimentModality, reset_working_memory


@dataclass
class ExperimentSession:
    session_id: str
    modality: ExperimentModality
    persona: PersonaRecord | None = None           # single-persona mode
    cohort: CohortEnvelope | None = None           # cohort mode
    stimuli: list[str] = field(default_factory=list)
    decision_scenarios: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.persona is None and self.cohort is None:
            raise ValueError("ExperimentSession requires either persona or cohort")
        if self.persona is not None and self.cohort is not None:
            raise ValueError("ExperimentSession takes persona OR cohort, not both")


def create_session(
    modality: ExperimentModality,
    stimuli: list[str],
    persona: PersonaRecord | None = None,
    cohort: CohortEnvelope | None = None,
    decision_scenarios: list[str] | None = None,
    session_id: str | None = None,
) -> ExperimentSession:
    """
    Factory function. Resets working memory before returning the session.

    For single-persona mode: resets the persona's working memory.
    For cohort mode: resets working memory for every persona in the cohort,
    then rebuilds the cohort envelope with the reset personas.

    session_id defaults to f"session-{uuid4().hex[:8]}"
    """
    if session_id is None:
        session_id = f"session-{uuid4().hex[:8]}"

    if decision_scenarios is None:
        decision_scenarios = []

    # Reset working memory so each experiment starts from a clean slate
    reset_persona: PersonaRecord | None = None
    reset_cohort: CohortEnvelope | None = None

    if persona is not None:
        reset_persona = reset_working_memory(persona)

    if cohort is not None:
        reset_personas = [reset_working_memory(p) for p in cohort.personas]
        reset_cohort = cohort.model_copy(update={"personas": reset_personas})

    return ExperimentSession(
        session_id=session_id,
        modality=modality,
        persona=reset_persona,
        cohort=reset_cohort,
        stimuli=stimuli,
        decision_scenarios=decision_scenarios,
    )
