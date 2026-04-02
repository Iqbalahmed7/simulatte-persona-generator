"""tests/test_memory_promotion.py — Sprint 11 memory promotion executor tests.

No LLM calls.  All synthetic data.
Tests for src/memory/promotion_executor.py and loop.py wiring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.schema.persona import (
    Observation,
    Reflection,
    WorkingMemory,
    SimulationState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_observation(
    content: str = "A sample observation.",
    importance: int = 5,
    emotional_valence: float = 0.0,
    obs_id: str | None = None,
) -> Observation:
    ts = _now()
    return Observation(
        id=obs_id or str(uuid.uuid4()),
        timestamp=ts,
        type="observation",
        content=content,
        importance=importance,
        emotional_valence=emotional_valence,
        last_accessed=ts,
    )


def _make_reflection(
    content: str = "A reflection.",
    importance: int = 7,
    source_observation_ids: list[str] | None = None,
) -> Reflection:
    # Reflection requires >= 2 source_observation_ids
    if source_observation_ids is None:
        source_observation_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    elif len(source_observation_ids) < 2:
        # Pad to minimum of 2 to satisfy schema validator
        source_observation_ids = source_observation_ids + [str(uuid.uuid4())]
    ts = _now()
    return Reflection(
        id=str(uuid.uuid4()),
        timestamp=ts,
        type="reflection",
        content=content,
        importance=importance,
        source_observation_ids=source_observation_ids,
        last_accessed=ts,
    )


def _make_simulation_state() -> SimulationState:
    return SimulationState(
        current_turn=0,
        importance_accumulator=0.0,
        reflection_count=0,
        awareness_set={},
        consideration_set=[],
        last_decision=None,
    )


def _make_working_memory(
    observations: list[Observation] | None = None,
    reflections: list[Reflection] | None = None,
) -> WorkingMemory:
    return WorkingMemory(
        observations=observations or [],
        reflections=reflections or [],
        plans=[],
        brand_memories={},
        simulation_state=_make_simulation_state(),
    )


# ---------------------------------------------------------------------------
# Test 1: get_promotable_observations — empty working memory
# ---------------------------------------------------------------------------

def test_get_promotable_empty():
    from src.memory.promotion_executor import get_promotable_observations

    working = _make_working_memory()
    result = get_promotable_observations(working)
    assert result == []


# ---------------------------------------------------------------------------
# Test 2: get_promotable_observations — importance too low
# ---------------------------------------------------------------------------

def test_get_promotable_importance_too_low():
    from src.memory.promotion_executor import get_promotable_observations

    obs = _make_observation(
        content="I tried a new brand and liked it.",
        importance=8,  # Below threshold of 9
    )
    working = _make_working_memory(observations=[obs])
    result = get_promotable_observations(working)
    assert result == []


# ---------------------------------------------------------------------------
# Test 3: get_promotable_observations — high importance but not enough citations
# ---------------------------------------------------------------------------

def test_get_promotable_not_enough_citations():
    from src.memory.promotion_executor import get_promotable_observations

    obs_id = str(uuid.uuid4())
    obs = _make_observation(
        content="This brand changed my mind about value.",
        importance=9,
        obs_id=obs_id,
    )
    # Only 2 reflections cite it (need >= 3); each reflection cites obs_id + a dummy
    reflections = [
        _make_reflection(
            content="I value quality more than I thought.",
            source_observation_ids=[obs_id, str(uuid.uuid4())],
            importance=8,
        ),
        _make_reflection(
            content="My brand preferences are shifting.",
            source_observation_ids=[obs_id, str(uuid.uuid4())],
            importance=7,
        ),
    ]
    working = _make_working_memory(observations=[obs], reflections=reflections)
    result = get_promotable_observations(working)
    assert result == []


# ---------------------------------------------------------------------------
# Test 4: promote_to_core — demographic content is skipped
# ---------------------------------------------------------------------------

def test_promote_to_core_skips_demographic():
    from src.memory.promotion_executor import promote_to_core
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    core = persona.memory.core
    original_summary = core.tendency_summary

    obs = _make_observation(
        content="My age is 34 and I live in Mumbai.",  # Contains demographic keywords
        importance=10,
        emotional_valence=0.5,
    )
    result = promote_to_core(core, obs)
    assert result is core or result.tendency_summary == original_summary


# ---------------------------------------------------------------------------
# Test 5: run_promotion_pass — full pass with eligible observation
# ---------------------------------------------------------------------------

def test_run_promotion_pass_promotes_eligible():
    from src.memory.promotion_executor import run_promotion_pass
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    core = persona.memory.core

    obs_id = str(uuid.uuid4())
    obs = _make_observation(
        content="This product consistently delivers on its promise.",
        importance=9,
        obs_id=obs_id,
    )
    # 3 reflections each citing obs_id (+ a dummy to meet min-2 requirement)
    reflections = [
        _make_reflection(
            content=f"Reflection {j}",
            source_observation_ids=[obs_id, str(uuid.uuid4())],
            importance=8,
        )
        for j in range(3)
    ]
    working = _make_working_memory(observations=[obs], reflections=reflections)
    updated_core, promoted_ids = run_promotion_pass(working, core)
    assert obs_id in promoted_ids
    assert obs.content in (updated_core.tendency_summary or "")


# ---------------------------------------------------------------------------
# Test 6: LoopResult has promoted_memory_ids field
# ---------------------------------------------------------------------------

def test_loop_result_has_promoted_ids_field():
    from src.cognition.loop import LoopResult

    # LoopResult requires an Observation for the first positional field.
    obs = _make_observation(content="Placeholder observation.", importance=5)
    result = LoopResult(observation=obs)
    assert hasattr(result, "promoted_memory_ids")
    assert isinstance(result.promoted_memory_ids, list)
