"""
loop.py — Cognitive Loop Orchestration for Simulatte.

Owns the full perceive → remember → reflect → decide cycle.
This is the entry point for running a persona through any stimulus.

Spec: Master Spec §9 (Cognitive Loop — all subsections).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.schema.persona import (
    Memory,
    Observation,
    PersonaRecord,
    Reflection,
    WorkingMemory,
)
from src.cognition.perceive import perceive
from src.cognition.reflect import reflect
from src.cognition.decide import decide, DecisionOutput
from src.experiment.session import SimulationTier, tier_models
from src.memory.working_memory import WorkingMemoryManager
from src.memory.retrieval import retrieve_top_k


@dataclass
class LoopResult:
    """Holds all outputs from a single cognitive loop run."""

    observation: Observation                              # always present
    reflections: list[Reflection] = field(default_factory=list)  # present if reflect fired
    decision: DecisionOutput | None = None               # present if decide was called
    reflected: bool = False                              # True if reflection cycle ran
    decided: bool = False                                # True if decision cycle ran
    promoted_memory_ids: list[str] = field(default_factory=list)
    """Observation IDs promoted to core memory this turn. Usually empty."""


async def run_loop(
    stimulus: str,
    persona: PersonaRecord,
    stimulus_id: str | None = None,
    decision_scenario: str | None = None,
    llm_client: Any = None,
    tier: SimulationTier = SimulationTier.DEEP,
) -> tuple[PersonaRecord, LoopResult]:
    """
    Run one full cognitive cycle for a persona encountering a stimulus.

    Steps:
    1. perceive(stimulus, persona) → Observation
    2. WorkingMemoryManager.write_observation(persona.memory.working, observation)
    3. WorkingMemoryManager.increment_accumulator(persona.memory.working, observation.importance)
    4. If WorkingMemoryManager.should_reflect(persona.memory.working):
       a. Retrieve top-20 observations
       b. reflect(observations, persona) → list[Reflection]
       c. WorkingMemoryManager.write_reflection(persona.memory.working, each reflection)
    5. If decision_scenario is provided:
       a. Retrieve top-10 memories relevant to decision_scenario
       b. decide(decision_scenario, memories, persona) → DecisionOutput
    6. Return (updated_persona, LoopResult)

    Returns a new PersonaRecord (immutable update via model_copy) with the
    updated working memory state.  The input PersonaRecord is never mutated.
    """
    manager = WorkingMemoryManager()

    # Resolve tier → per-stage model names
    _models = tier_models(tier)

    # ------------------------------------------------------------------
    # Step 1: Perceive
    # ------------------------------------------------------------------
    observation: Observation = await perceive(stimulus, persona, stimulus_id=stimulus_id, llm_client=llm_client)

    # ------------------------------------------------------------------
    # Step 2: Write observation to working memory
    # ------------------------------------------------------------------
    working: WorkingMemory = persona.memory.working

    working = manager.write_observation(working, observation)

    # ------------------------------------------------------------------
    # Step 3: Increment importance accumulator
    # ------------------------------------------------------------------
    working = manager.increment_accumulator(working, observation.importance)

    # ------------------------------------------------------------------
    # Step 4: Conditional reflection
    # ------------------------------------------------------------------
    new_reflections: list[Reflection] = []
    reflected = False

    if manager.should_reflect(working):
        # Retrieve top-20 observations for reflect (recency + importance + relevance)
        top_20 = manager.retrieve_top_k(working, query="", k=20)

        # Only pass Observation objects (retrieve_top_k may return mixed types)
        obs_for_reflect: list[Observation] = [
            entry for entry in top_20 if entry.type == "observation"
        ]

        raw_reflections: list[Reflection] = await reflect(
            obs_for_reflect, persona,
            llm_client=llm_client,
            model=_models["reflect"],
        )

        for ref in raw_reflections:
            working = manager.write_reflection(working, ref)
            new_reflections.append(ref)

        reflected = True

    # ------------------------------------------------------------------
    # Step 4b: Memory promotion pass
    # ------------------------------------------------------------------
    # After reflecting, check if any observations meet the promotion threshold.
    # Promotable observations (importance >= 9, >= 3 citations) are written
    # to core memory. This is a no-op if no observations qualify.
    # Settled at §14A S17.
    promoted_ids: list[str] = []
    if working.reflections:  # Only run if there are reflections (citations needed)
        from src.memory.promotion_executor import run_promotion_pass
        new_core, promoted_ids = run_promotion_pass(working, persona.memory.core)
        if promoted_ids:
            # Update persona core memory — model_copy, never mutate
            new_mem_with_core = persona.memory.model_copy(update={"core": new_core})
            persona = persona.model_copy(update={"memory": new_mem_with_core})
            working = persona.memory.working  # re-sync working ref

    # ------------------------------------------------------------------
    # Step 5: Conditional decision
    # ------------------------------------------------------------------
    decision_output: DecisionOutput | None = None
    decided = False

    if decision_scenario is not None:
        # Retrieve top-10 memories relevant to the decision scenario.
        # Passes mixed observations + reflections to the module-level retrieve_top_k
        # (not the manager method) as specified in the brief.
        all_memories: list[Observation | Reflection] = [
            *working.observations,
            *working.reflections,
        ]
        top_10 = retrieve_top_k(all_memories, query=decision_scenario, k=10)

        decision_output = await decide(
            decision_scenario, top_10, persona,
            llm_client=llm_client,
            model=_models["decide"],
        )
        decided = True

    # ------------------------------------------------------------------
    # Step 6: Increment current_turn and return updated PersonaRecord
    # ------------------------------------------------------------------
    new_state = working.simulation_state.model_copy(
        update={"current_turn": working.simulation_state.current_turn + 1}
    )
    working = working.model_copy(update={"simulation_state": new_state})

    # Produce a new PersonaRecord — never mutate the input
    new_memory = persona.memory.model_copy(update={"working": working})
    updated_persona = persona.model_copy(update={"memory": new_memory})

    loop_result = LoopResult(
        observation=observation,
        reflections=new_reflections,
        decision=decision_output,
        reflected=reflected,
        decided=decided,
        promoted_memory_ids=promoted_ids,
    )

    return updated_persona, loop_result
