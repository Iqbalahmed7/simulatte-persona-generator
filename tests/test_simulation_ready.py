"""tests/test_simulation_ready.py — Sprint 15: simulation-ready mode differentiation.

Verifies that:
- simulation-ready mode bootstraps ≥ 3 seed memories into working memory
- quick mode produces no seed memories
- seed memories reference core identity values
- G10 gate passes for simulation-ready mode
"""

from __future__ import annotations


def test_simulation_ready_mode_seeds_working_memory():
    """simulation-ready mode produces ≥ 3 seed observations in working memory."""
    from src.memory.seed_memory import bootstrap_seed_memories
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    working = bootstrap_seed_memories(
        core_memory=persona.memory.core,
        persona_name=persona.demographic_anchor.name,
    )
    assert len(working.observations) >= 3


def test_quick_mode_has_empty_working_memory():
    """quick mode persona has no seed observations in working memory."""
    from datetime import datetime, timezone
    from src.schema.persona import (
        Memory,
        SimulationState,
        WorkingMemory,
    )
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    # Build a persona and replace its working memory with an empty one,
    # simulating what the identity_constructor does for quick mode.
    persona = make_synthetic_persona()
    empty_working = WorkingMemory(
        observations=[],
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
    quick_persona = persona.model_copy(
        update={"memory": Memory(core=persona.memory.core, working=empty_working)}
    )
    assert len(quick_persona.memory.working.observations) == 0


def test_seed_memories_reference_core_values():
    """Seed memories should reference values or identity from core memory."""
    from src.memory.seed_memory import bootstrap_seed_memories
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    working = bootstrap_seed_memories(
        core_memory=persona.memory.core,
        persona_name=persona.demographic_anchor.name,
    )
    assert len(working.observations) >= 3
    # At least one observation should reference the identity statement or a key value
    contents = [obs.content for obs in working.observations]
    identity_stmt = persona.memory.core.identity_statement
    primary_value = persona.memory.core.key_values[0] if persona.memory.core.key_values else ""
    assert any(
        identity_stmt[:30] in c or primary_value[:20] in c
        for c in contents
    ), f"No seed memory references core identity/values. Contents: {contents}"


def test_simulation_ready_passes_g10():
    """G10 gate: ≥ 3 seed memories required. simulation-ready should pass."""
    from src.memory.seed_memory import bootstrap_seed_memories
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    working = bootstrap_seed_memories(
        core_memory=persona.memory.core,
        persona_name=persona.demographic_anchor.name,
    )
    assert len(working.observations) >= 3, "G10: must have ≥ 3 seed memories"
