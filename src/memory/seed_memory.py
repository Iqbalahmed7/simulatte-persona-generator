"""src/memory/seed_memory.py — Seed memory bootstrap for simulation start.

Sprint 3 — OpenCode (Core Memory + Seed Memory Engineer)

Bootstraps a fresh WorkingMemory pre-populated with ≥ 3 seed observations
derived from CoreMemory. Called at simulation start (Sprint 6/7 modality
layer), not during persona creation.

G10 gate: WorkingMemory must have ≥ 3 observations after bootstrap.

Zero LLM calls.

Note on WorkingMemoryManager:
  The brief references `from src.memory.working_memory import WorkingMemoryManager`
  but that module is a Sprint 6/7 deliverable.  Until it exists we construct
  WorkingMemory directly from the Pydantic schema.  When WorkingMemoryManager
  lands, this file should be updated to delegate construction to it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.schema.persona import (
    CoreMemory,
    Observation,
    SimulationState,
    WorkingMemory,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEED_IMPORTANCE = 8          # High importance, just below promotion threshold of 9.
_SEED_VALENCE = 0.0           # Neutral emotional valence for identity anchors.
_MAX_LIFE_EVENT_SEEDS = 3     # Cap on life-event-derived seeds.
_G10_MINIMUM = 3              # Gate: must have at least this many observations.


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def bootstrap_seed_memories(
    core_memory: CoreMemory,
    persona_name: str,
) -> WorkingMemory:
    """Create a fresh WorkingMemory pre-populated with ≥ 3 seed observations.

    Seed observations represent:
    1. Identity anchor — derived from identity_statement
    2. Primary value — derived from key_values[0]
    3. Key tension — first sentence of tendency_summary
    4+ Optional: one per life_defining_event (up to 3 additional)

    G10 gate: asserts ≥ 3 observations exist after bootstrap.
    If derivation somehow produces fewer, fallback seeds are added.

    Returns a WorkingMemory ready for simulation.
    """
    observations: list[Observation] = []

    # ------------------------------------------------------------------
    # Seed 1 — Identity anchor
    # ------------------------------------------------------------------
    observations.append(
        _make_seed_observation(
            content=f"I know myself: {core_memory.identity_statement}",
            importance=_SEED_IMPORTANCE,
            emotional_valence=_SEED_VALENCE,
        )
    )

    # ------------------------------------------------------------------
    # Seed 2 — Primary value
    # ------------------------------------------------------------------
    primary_value = core_memory.key_values[0] if core_memory.key_values else "my core values"
    observations.append(
        _make_seed_observation(
            content=f"What matters most to me: {primary_value}",
            importance=_SEED_IMPORTANCE,
            emotional_valence=_SEED_VALENCE,
        )
    )

    # ------------------------------------------------------------------
    # Seed 3 — Core tension (first sentence of tendency_summary)
    # ------------------------------------------------------------------
    first_sentence = _extract_first_sentence(core_memory.tendency_summary)
    observations.append(
        _make_seed_observation(
            content=f"Something I always navigate: {first_sentence}",
            importance=_SEED_IMPORTANCE,
            emotional_valence=_SEED_VALENCE,
        )
    )

    # ------------------------------------------------------------------
    # Seeds 4+ — Life defining events (up to 3)
    # ------------------------------------------------------------------
    for event in core_memory.life_defining_events[:_MAX_LIFE_EVENT_SEEDS]:
        observations.append(
            _make_seed_observation(
                content=(
                    f"A defining moment in my life: {event.event} — {event.lasting_impact}"
                ),
                importance=_SEED_IMPORTANCE,
                emotional_valence=_SEED_VALENCE,
            )
        )

    # ------------------------------------------------------------------
    # G10 gate — guarantee ≥ 3 observations
    # ------------------------------------------------------------------
    _ensure_g10_gate(observations, core_memory, persona_name)

    # ------------------------------------------------------------------
    # Assemble WorkingMemory
    # ------------------------------------------------------------------
    return WorkingMemory(
        observations=observations,
        reflections=[],
        plans=[],
        brand_memories={},
        simulation_state=SimulationState(
            current_turn=0,
            importance_accumulator=0.0,
            reflection_count=0,
            awareness_set={},
            consideration_set=[],
            last_decision=None,
        ),
    )


def _make_seed_observation(
    content: str,
    importance: int = _SEED_IMPORTANCE,
    emotional_valence: float = _SEED_VALENCE,
) -> Observation:
    """Create a seed Observation with fixed attributes.

    - id: uuid4
    - timestamp: now (UTC)
    - type: "observation"
    - source_stimulus_id: None (seed memories have no stimulus)
    - last_accessed: now (UTC)
    """
    now = datetime.now(tz=timezone.utc)
    return Observation(
        id=str(uuid.uuid4()),
        timestamp=now,
        type="observation",
        content=content,
        importance=importance,
        emotional_valence=emotional_valence,
        source_stimulus_id=None,
        last_accessed=now,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_first_sentence(text: str) -> str:
    """Return the first sentence of text.

    Splits on the first occurrence of '.', '!', or '?'.
    Falls back to the full text if no sentence boundary is found.
    """
    if not text:
        return text

    # Find the first sentence-ending punctuation.
    for i, ch in enumerate(text):
        if ch in (".", "!", "?"):
            # Include the punctuation character.
            return text[: i + 1].strip()

    # No sentence boundary found — return full text stripped.
    return text.strip()


def _ensure_g10_gate(
    observations: list[Observation],
    core_memory: CoreMemory,
    persona_name: str,
) -> None:
    """Guarantee ≥ _G10_MINIMUM observations (G10 gate).

    If derivation somehow produced fewer (e.g. empty key_values or
    tendency_summary), add fallback seeds until the count is met.
    Modifies the observations list in-place.
    """
    fallback_pool: list[str] = [
        f"I am {persona_name} and I navigate decisions guided by my values.",
        f"My core identity shapes every decision I make.",
        (
            f"I hold myself to my values: "
            f"{', '.join(core_memory.key_values[:2]) if core_memory.key_values else 'integrity and purpose'}."
        ),
    ]

    idx = 0
    while len(observations) < _G10_MINIMUM and idx < len(fallback_pool):
        observations.append(
            _make_seed_observation(
                content=fallback_pool[idx],
                importance=_SEED_IMPORTANCE,
                emotional_valence=_SEED_VALENCE,
            )
        )
        idx += 1

    # Final assertion — should never fail given the 3 fixed seeds above,
    # but serves as a runtime safety net.
    if len(observations) < _G10_MINIMUM:
        raise RuntimeError(
            f"G10 gate failure: bootstrap_seed_memories produced only "
            f"{len(observations)} observation(s); minimum is {_G10_MINIMUM}."
        )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = ["bootstrap_seed_memories", "_make_seed_observation"]
