"""
reflection_store.py — Promotion gate and citation utilities for Simulatte.

Rules settled at §14A S17.

No LLM calls.  No state.  All functions are pure.
"""

from src.schema.persona import Reflection


def can_promote(
    importance: int,
    citation_count: int,
    no_contradiction: bool,
) -> bool:
    """
    Promotion gate: returns True only when ALL three conditions are met:
    1. importance >= 9        (just above seed memory default of 8)
    2. citation_count >= 3    (cited by >= 3 distinct reflections)
    3. no_contradiction       (no contradicting entry in memory)

    Demographics are never promoted — this gate is called only for
    observations and reflections, never for core memory fields.

    Rules settled at §14A S17.
    """
    return importance >= 9 and citation_count >= 3 and no_contradiction


def citation_count(
    observation_id: str,
    reflections: list[Reflection],
) -> int:
    """
    Count how many reflections cite a given observation_id.
    """
    return sum(
        1 for r in reflections
        if observation_id in r.source_observation_ids
    )
