"""
working_memory.py — CRUD operations on WorkingMemory for Simulatte.

Owns: write_observation, write_reflection, retrieve_top_k, evict, reset,
      increment_accumulator, should_reflect.

No LLM calls.  All timestamps use datetime.now(timezone.utc).
WorkingMemory is a Pydantic model; updates use .model_copy(update={...})
so callers that hold a reference to the old object are not surprised.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.schema.persona import (
    Observation,
    Reflection,
    SimulationState,
    WorkingMemory,
)
from src.memory.retrieval import (
    retrieve_top_k as _retrieval_top_k,
    recency_score as _recency_score,
    DEFAULT_DECAY_LAMBDA,
)

# Maximum observations before auto-eviction is triggered
_OBS_HARD_CAP: int = 1000
# Default target after eviction
_OBS_EVICT_TARGET: int = 900


def _adaptive_threshold(expected_stimuli: int | None) -> float:
    """Compute reflection threshold adaptively based on simulation length.

    Master Spec §14A O6: reflection threshold is an open question.
    Default 50 is calibrated for ~10-stimulus simulations. But short
    simulations (3 stimuli) never accumulate enough importance, and
    long simulations (20+) over-reflect.

    Scaling:
      1-3 stimuli  → 15  (reflect early in short runs)
      4-8 stimuli  → 35  (balanced)
      9-20 stimuli → 50  (standard)
      20+ stimuli  → 75  (avoid over-reflecting)
    """
    if expected_stimuli is None:
        return 50.0
    if expected_stimuli <= 3:
        return 15.0
    if expected_stimuli <= 8:
        return 35.0
    if expected_stimuli <= 20:
        return 50.0
    return 75.0


class WorkingMemoryManager:
    """
    All working-memory operations.  Stateless — the WorkingMemory object
    is passed in and a new (updated) copy is returned.
    """

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def write_observation(
        self,
        working: WorkingMemory,
        obs: Observation,
    ) -> WorkingMemory:
        """
        Appends an already-constructed Observation to working.observations.
        Triggers eviction if len(observations) > 1000 after the write.
        Returns updated WorkingMemory.

        To construct an Observation before calling, use Observation(...) directly.
        """
        new_observations = list(working.observations) + [obs]
        updated = working.model_copy(update={"observations": new_observations})

        if len(updated.observations) > _OBS_HARD_CAP:
            updated, _ = self.evict(updated, target_size=_OBS_EVICT_TARGET)

        return updated

    def write_reflection(
        self,
        working: WorkingMemory,
        ref: Reflection,
    ) -> WorkingMemory:
        """
        Appends an already-constructed Reflection to working.reflections.
        Increments simulation_state.reflection_count.
        Resets simulation_state.importance_accumulator to 0.0.
        Returns updated WorkingMemory.

        To construct a Reflection before calling, use Reflection(...) directly.
        Note: Reflection schema enforces len(source_observation_ids) >= 2.
        """
        new_reflections = list(working.reflections) + [ref]

        new_state = working.simulation_state.model_copy(
            update={
                "reflection_count": working.simulation_state.reflection_count + 1,
                "importance_accumulator": 0.0,
            }
        )

        return working.model_copy(
            update={
                "reflections": new_reflections,
                "simulation_state": new_state,
            }
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve_top_k(
        self,
        working: WorkingMemory,
        query: str,
        k: int = 10,
        now: datetime | None = None,
    ) -> list[Observation | Reflection]:
        """
        Returns top-K memory entries (observations + reflections) by
        retrieval score: α·recency + β·importance + γ·relevance.
        Default α=β=γ=1/3.

        Uses model_copy (immutable-update pattern) — does not mutate the
        passed WorkingMemory object in place.  Returns the scored entries
        with updated last_accessed timestamps.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        all_entries: list[Observation | Reflection] = (
            list(working.observations) + list(working.reflections)
        )

        top = _retrieval_top_k(all_entries, query, k, now=now)

        if not top:
            return top

        # Update last_accessed on returned entries via model_copy.
        returned_ids: set[str] = {e.id for e in top}

        new_observations = [
            obs.model_copy(update={"last_accessed": now})
            if obs.id in returned_ids
            else obs
            for obs in working.observations
        ]
        new_reflections = [
            ref.model_copy(update={"last_accessed": now})
            if ref.id in returned_ids
            else ref
            for ref in working.reflections
        ]

        # Re-map so the returned list contains the updated objects.
        updated_map: dict[str, Observation | Reflection] = {}
        for obs in new_observations:
            if obs.id in returned_ids:
                updated_map[obs.id] = obs
        for ref in new_reflections:
            if ref.id in returned_ids:
                updated_map[ref.id] = ref

        return [updated_map[e.id] for e in top]

    # ------------------------------------------------------------------
    # Eviction
    # ------------------------------------------------------------------

    def evict(
        self,
        memory: WorkingMemory,
        target_size: int = _OBS_EVICT_TARGET,
    ) -> tuple[WorkingMemory, int]:
        """
        Evicts lowest-scoring observations until len(observations) ≤ target_size.

        Eviction score = importance × recency_score  (no query — no relevance)

        Removes bottom 10% by eviction score, then continues removing the
        lowest scorer one-by-one until target_size is reached.

        Never evicts reflections.
        Returns (updated_memory, n_evicted).
        """
        observations = list(memory.observations)
        n_start = len(observations)

        if n_start <= target_size:
            # Nothing to do
            return memory, 0

        now = datetime.now(timezone.utc)

        def _eviction_score(obs: Observation) -> float:
            return obs.importance * _recency_score(obs, now, DEFAULT_DECAY_LAMBDA)

        # Score and sort ascending (worst first for eviction)
        scored = sorted(observations, key=_eviction_score)

        # Bottom 10% of total (at least 1)
        bottom_10pct = max(1, int(len(scored) * 0.10))
        # Also need to remove enough to reach target_size
        must_remove = n_start - target_size
        n_to_remove = max(bottom_10pct, must_remove)
        # Cap at total length
        n_to_remove = min(n_to_remove, len(scored))

        # Keep the top (len - n_to_remove) entries
        surviving = scored[n_to_remove:]
        n_evicted = n_start - len(surviving)

        updated = memory.model_copy(update={"observations": surviving})
        return updated, n_evicted

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(
        self,
        memory: WorkingMemory,
    ) -> WorkingMemory:
        """
        Resets working memory for a new experiment.
        Clears observations, reflections, plans, brand_memories,
        and simulation_state.
        Core memory is NOT touched — this method does not receive it.
        Idempotent: calling twice produces the same result as calling once.
        """
        fresh_state = SimulationState(
            current_turn=0,
            importance_accumulator=0.0,
            reflection_count=0,
            awareness_set={},
            consideration_set=[],
            last_decision=None,
        )
        return memory.model_copy(
            update={
                "observations": [],
                "reflections": [],
                "plans": [],
                "brand_memories": {},
                "simulation_state": fresh_state,
            }
        )

    # ------------------------------------------------------------------
    # Accumulator helpers
    # ------------------------------------------------------------------

    def increment_accumulator(
        self,
        working: WorkingMemory,
        amount: float,
    ) -> WorkingMemory:
        """
        Adds amount to simulation_state.importance_accumulator.
        Called after every perceive() in the cognitive loop.
        Returns updated WorkingMemory.
        """
        new_acc = working.simulation_state.importance_accumulator + amount
        new_state = working.simulation_state.model_copy(
            update={"importance_accumulator": new_acc}
        )
        return working.model_copy(update={"simulation_state": new_state})

    def should_reflect(
        self,
        working: WorkingMemory,
        threshold: float | None = None,
        obs_count_trigger: int = 3,
        expected_stimuli: int | None = None,
    ) -> bool:
        """
        Returns True if importance_accumulator > threshold OR if the persona
        has accumulated >= obs_count_trigger observations and hasn't reflected yet.

        The obs_count_trigger path ensures reflection fires in short simulations
        (e.g. 3-round case studies) where the importance accumulator never reaches
        the threshold before decisions are made.

        Adaptive threshold (new):
          If threshold is None, it's computed from expected_stimuli:
            - 1-3 stimuli  → threshold = 15 (reflect early in short runs)
            - 4-8 stimuli  → threshold = 35 (balanced)
            - 9-20 stimuli → threshold = 50 (standard, per Master Spec §14A O6)
            - 20+ stimuli  → threshold = 75 (avoid over-reflecting in long runs)
          If expected_stimuli is also None, defaults to 50.0.

        threshold: explicit override (Open Question O6).
        obs_count_trigger: 3 (fire on 3rd observation if no prior reflection).
        expected_stimuli: total stimuli in this simulation (for adaptive threshold).
        """
        effective_threshold = threshold
        if effective_threshold is None:
            effective_threshold = _adaptive_threshold(expected_stimuli)

        if working.simulation_state.importance_accumulator > effective_threshold:
            return True
        n_obs = len(working.observations)
        no_prior_reflection = working.simulation_state.reflection_count == 0
        return n_obs >= obs_count_trigger and no_prior_reflection
