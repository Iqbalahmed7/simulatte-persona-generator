"""
BV1: Repeated-run stability test.

Runs the same decision scenario 3 times for the same persona.
Asserts: >= 2/3 runs produce the same final decision (normalized match).

Requires: live Anthropic API key. Run with: pytest --integration
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from collections import Counter

from tests.fixtures.synthetic_persona import make_synthetic_persona


def _normalize_decision(text: str) -> str:
    """
    Normalize a decision string for stable comparison.

    Rules:
    - If text starts with "yes" (case-insensitive, after strip) → return "yes"
    - If text starts with "no"  (case-insensitive, after strip) → return "no"
    - Else → return the first 30 characters of the lowercased, stripped text

    This handles LLM responses that begin "Yes, I will..." or "No, I would not..."
    as well as freeform final_decision text that does not start with yes/no.
    """
    normalized = text.lower().strip()
    if normalized.startswith("yes"):
        return "yes"
    if normalized.startswith("no"):
        return "no"
    return normalized[:30]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bv1_decision_stability() -> None:
    """
    Same persona, same stimulus, same decision scenario.
    Run 3 times. Assert >= 2/3 return the same normalized decision.

    BV1 threshold: most common decision appears in at least 2 of 3 runs.

    Normalization strategy:
    - "yes..." → "yes"
    - "no..."  → "no"
    - other   → first 30 chars (truncated match)

    This makes the check robust to minor phrasing variations while still
    detecting genuine instability (e.g. yes / no / yes vs yes / yes / yes).
    """
    # Import here so the test file can be collected even when cognition modules
    # are not yet fully delivered (parallel sprint development).
    try:
        from src.cognition.loop import run_loop, LoopResult  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"src.cognition.loop not yet available: {exc}")

    persona = make_synthetic_persona()
    stimulus = "A new premium coffee brand is offering a free trial sample."
    scenario = "Do you sign up for the free trial?"

    decisions: list[str] = []
    for _ in range(3):
        _, result = await run_loop(
            stimulus=stimulus,
            persona=persona,
            decision_scenario=scenario,
        )
        raw_decision = result.decision.decision.lower().strip()
        decisions.append(_normalize_decision(raw_decision))

    most_common, count = Counter(decisions).most_common(1)[0]
    assert count >= 2, (
        f"BV1 FAIL: decisions were not stable. "
        f"Got (normalized): {decisions}. "
        f"Most common '{most_common}' appeared only {count}/3 times."
    )
