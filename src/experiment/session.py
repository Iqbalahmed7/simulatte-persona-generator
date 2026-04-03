"""src/experiment/session.py — Experiment session factory.

Ties a persona (or cohort), a modality, and a stimulus sequence into an
experiment session. Resets working memory before handing the session back
to the caller so each experiment starts from a clean slate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from src.schema.cohort import CohortEnvelope
from src.schema.persona import PersonaRecord
from src.experiment.modality import ExperimentModality, reset_working_memory
from src.social.schema import SocialNetwork, SocialSimulationLevel

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_SONNET_MODEL = "claude-sonnet-4-6"


class SimulationTier(str, Enum):
    """Model routing tier for cognitive simulation.

    Controls which LLM model is used at each stage of the cognitive loop.
    Allows cost/quality tradeoffs for different use cases (Open Question O8).

    DEEP   — Current default. Haiku for perceive, Sonnet for reflect+decide.
             Best insight quality. Use for per-persona deep analysis.
    SIGNAL — Haiku throughout with Sonnet for final decide only.
             Good signal quality at lower cost. Use for mid-scale runs.
    VOLUME — Haiku throughout including decide.
             Fastest and cheapest. Use for 1,000+ persona distribution runs
             where directional signal matters more than individual depth.
    """
    DEEP = "deep"
    SIGNAL = "signal"
    VOLUME = "volume"


def tier_models(tier: SimulationTier) -> dict[str, str]:
    """Return the model names for each cognitive stage given a tier.

    Returns a dict with keys: 'perceive', 'reflect', 'decide'.
    perceive is always Haiku (per spec §9) — the tier only varies reflect/decide.
    """
    if tier == SimulationTier.VOLUME:
        return {"perceive": _HAIKU_MODEL, "reflect": _HAIKU_MODEL, "decide": _HAIKU_MODEL}
    if tier == SimulationTier.SIGNAL:
        return {"perceive": _HAIKU_MODEL, "reflect": _HAIKU_MODEL, "decide": _SONNET_MODEL}
    # DEEP (default)
    return {"perceive": _HAIKU_MODEL, "reflect": _SONNET_MODEL, "decide": _SONNET_MODEL}


@dataclass
class ExperimentSession:
    session_id: str
    modality: ExperimentModality
    persona: PersonaRecord | None = None           # single-persona mode
    cohort: CohortEnvelope | None = None           # cohort mode
    stimuli: list[str] = field(default_factory=list)
    decision_scenarios: list[str] = field(default_factory=list)
    tier: SimulationTier = SimulationTier.DEEP
    social_simulation_level: SocialSimulationLevel = field(default_factory=lambda: SocialSimulationLevel.ISOLATED)
    social_network: SocialNetwork | None = None
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
    tier: SimulationTier = SimulationTier.DEEP,
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
        tier=tier,
    )
