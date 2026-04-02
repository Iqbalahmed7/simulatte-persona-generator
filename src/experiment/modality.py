"""src/experiment/modality.py — Experiment modality enum and working memory reset.

Defines the four experiment modalities and the reset_working_memory operation
that clears a persona's working memory for a fresh experiment run.

Design note (§14A S18): Core memory is immutable by design. reset_working_memory
never touches persona.memory.core — only persona.memory.working is cleared.
"""

from __future__ import annotations

from enum import Enum

from src.schema.persona import Memory, PersonaRecord, SimulationState, WorkingMemory


class ExperimentModality(Enum):
    ONE_TIME_SURVEY = "one_time_survey"
    TEMPORAL_SIMULATION = "temporal_simulation"
    POST_EVENT_SURVEY = "post_event_survey"
    DEEP_INTERVIEW = "deep_interview"


def reset_working_memory(persona: PersonaRecord) -> PersonaRecord:
    """
    Reset a persona's working memory for a new experiment.

    Clears: observations, reflections, plans, brand_memories.
    Resets SimulationState: current_turn=0, importance_accumulator=0.0,
      reflection_count=0, awareness_set={}, consideration_set=[], last_decision=None.

    Core memory is NEVER touched — immutable by design (§14A S18).
    Returns a new PersonaRecord via model_copy. Never mutates the input.

    Idempotent: calling reset on an already-empty working memory produces
    the same result as the first reset.
    """
    empty_state = SimulationState(
        current_turn=0,
        importance_accumulator=0.0,
        reflection_count=0,
        awareness_set={},
        consideration_set=[],
        last_decision=None,
    )
    empty_working = WorkingMemory(
        observations=[],
        reflections=[],
        plans=[],
        brand_memories={},
        simulation_state=empty_state,
    )
    new_memory = persona.memory.model_copy(update={"working": empty_working})
    return persona.model_copy(update={"memory": new_memory})
