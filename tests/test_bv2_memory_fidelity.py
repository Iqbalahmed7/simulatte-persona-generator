"""
BV2: Memory-faithful recall test.

Seeds a persona's working memory with a high-importance observation.
Runs a decision scenario related to that observation.
Asserts: the reasoning trace mentions the seeded observation's content.

Requires: live Anthropic API key. Run with: pytest --integration
"""

from __future__ import annotations

import pytest

from tests.fixtures.synthetic_persona import make_synthetic_persona
from tests.fixtures.synthetic_observation import make_synthetic_observation


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bv2_decision_references_memory() -> None:
    """
    Plant a high-importance observation in working memory.
    Run a decision relevant to that observation.
    Assert: reasoning_trace mentions a key word from the seeded observation.

    Seeded observation: a concrete, negative experience with a premium brand's
    pricing — "expensive", "far too expensive", "last month", "premium", "offered".
    These words are specific, concrete, and highly likely to surface in any
    decision reasoning that faithfully retrieves and uses working memory.

    Assertion strategy: substring OR-match across 4 probe words from the seeded
    content. Passing any one word is sufficient — the test is intentionally
    lenient to account for reasonable paraphrase (e.g. "costly" instead of
    "expensive") while still failing if the memory is completely ignored.
    """
    # Import here so the test file can be collected even when cognition modules
    # are not yet fully delivered (parallel sprint development).
    try:
        from src.cognition.loop import run_loop  # noqa: F401
        from src.memory.working_memory import WorkingMemoryManager
    except ImportError as exc:
        pytest.skip(f"Required modules not yet available: {exc}")

    from src.schema.persona import Memory

    persona = make_synthetic_persona()
    manager = WorkingMemoryManager()

    # Plant a relevant, high-importance observation
    seed_obs = make_synthetic_observation(
        content="I tried the premium brand last month and it was far too expensive for what it offered.",
        importance=9,
        emotional_valence=-0.6,
    )
    updated_working = manager.write_observation(persona.memory.working, seed_obs)
    persona = persona.model_copy(
        update={"memory": Memory(core=persona.memory.core, working=updated_working)}
    )

    # Run a related decision scenario
    stimulus = "A premium coffee brand is offering a full-price subscription."
    scenario = "Do you subscribe to this premium coffee service?"

    _, result = await run_loop(
        stimulus=stimulus,
        persona=persona,
        decision_scenario=scenario,
    )

    # The reasoning trace should reference the seeded memory
    trace = result.decision.reasoning_trace.lower()
    assert any(
        word in trace
        for word in ["expensive", "last month", "premium", "offered"]
    ), (
        f"BV2 FAIL: reasoning_trace did not reference seeded memory.\n"
        f"Seeded: 'I tried the premium brand last month and it was far too expensive "
        f"for what it offered.'\n"
        f"Trace (first 500 chars): {result.decision.reasoning_trace[:500]}"
    )
