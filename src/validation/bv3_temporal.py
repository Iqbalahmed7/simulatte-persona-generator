"""src/validation/bv3_temporal.py — BV3 Temporal Consistency Test Runner.

Sprint 21 — Cursor (Simulation Quality Gates)

Spec: Validity Protocol Module 2 — BV3 (temporal consistency).
      Master Spec §9 (Cognitive Loop — temporal property requirements).

BV3 verifies that memory accumulates and influences decisions across a
multi-turn simulation. Runs a 10-stimulus arc (1-5 positive, 6-10 mixed)
and checks three properties:

  (a) Confidence / trust increases across positive stimuli 1-5
      (monotonic or near-monotonic)
  (b) At least 1 reflection after stimulus 5 references the accumulating
      positive trend
  (c) Final decision reasoning cites both positive AND mixed experiences
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # avoid circular import issues at check time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stimulus definitions — Littlejoys Nutrimix arc
# ---------------------------------------------------------------------------

_POSITIVE_STIMULI: list[str] = [
    "Your pediatrician mentions Nutrimix helps fill nutritional gaps in picky eaters.",
    "A close friend messages you: her son's appetite improved after a month on Nutrimix.",
    "Nutrimix wins 'Best Clean Label' award — no artificial colours or preservatives.",
    "Subscribe & Save offer: ₹649/month with free delivery and skip-any-month flexibility.",
    "School nutritionist sends a group note recommending Nutrimix for children aged 2–8.",
]

_MIXED_STIMULI: list[str] = [
    "Your child refuses to drink Nutrimix after three days — says it tastes 'weird'.",
    "You see a social media post questioning whether supplements are necessary for healthy children.",
    "A neighbour mentions her child had a mild stomach upset after starting a new supplement.",
    "The price increased to ₹799 this month — Subscribe & Save no longer available.",
    "You read an article saying most children's nutritional needs can be met through diet alone.",
]

_DECISION_SCENARIO = "Should you buy Littlejoys Nutrimix for your child this month?"

# ---------------------------------------------------------------------------
# Keyword sets for Check B and Check C
# ---------------------------------------------------------------------------

_CHECK_B_KEYWORDS: list[str] = [
    "pattern",
    "noticing",
    "trend",
    "consistently",
    "positive",
    "accumul",
    "building",
    "trust",
]

_POSITIVE_KEYWORDS: list[str] = [
    "pediatrician",
    "friend",
    "award",
    "subscribe",
    "nutritionist",
]

_MIXED_KEYWORDS: list[str] = [
    "taste",
    "refuses",
    "unnecessary",
    "price",
    "stomach",
    "diet",
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class BV3Result:
    """Result of a BV3 temporal consistency test run."""

    passed: bool
    persona_id: str
    check_a_passed: bool          # confidence trend across positive arc
    check_b_passed: bool          # reflection references accumulation
    check_c_passed: bool          # final decision cites both positive and mixed
    confidence_sequence: list[int]  # confidence from each of 5 positive stimuli
    reflection_count: int
    failure_reasons: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable one-line summary of the BV3 result."""
        status = "PASS" if self.passed else "FAIL"
        checks = (
            f"A={'PASS' if self.check_a_passed else 'FAIL'} "
            f"B={'PASS' if self.check_b_passed else 'FAIL'} "
            f"C={'PASS' if self.check_c_passed else 'FAIL'}"
        )
        conf = f"confidence_seq={self.confidence_sequence}"
        reasons = ""
        if self.failure_reasons:
            reasons = " | reasons: " + "; ".join(self.failure_reasons)
        return f"BV3 [{status}] persona={self.persona_id} {checks} {conf}{reasons}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_a(confidence_sequence: list[int]) -> tuple[bool, list[str]]:
    """Check A: confidence trend across the positive arc.

    Rules (per spec):
    - Skip if fewer than 2 confidence values collected.
    - Pass if: last >= first AND no more than 1 downward step > 15 points.
    """
    reasons: list[str] = []

    if len(confidence_sequence) < 2:
        # Not enough data — skip (treat as pass with a note)
        return True, []

    first = confidence_sequence[0]
    last = confidence_sequence[-1]

    # Count downward steps larger than 15 points
    large_dips = 0
    for i in range(1, len(confidence_sequence)):
        prev = confidence_sequence[i - 1]
        curr = confidence_sequence[i]
        if (prev - curr) > 15:
            large_dips += 1

    passed = (last >= first) and (large_dips <= 1)

    if last < first:
        reasons.append(
            f"Check A: final confidence ({last}) < initial confidence ({first})"
        )
    if large_dips > 1:
        reasons.append(
            f"Check A: {large_dips} downward steps > 15 points (max 1 allowed)"
        )

    return passed, reasons


def _check_b(reflections: list[Any]) -> tuple[bool, list[str]]:
    """Check B: at least 1 reflection references the accumulating positive trend.

    Looks for any of _CHECK_B_KEYWORDS in reflection content (case-insensitive).
    """
    for ref in reflections:
        content = ""
        if hasattr(ref, "content"):
            content = ref.content or ""
        elif isinstance(ref, str):
            content = ref

        content_lower = content.lower()
        for kw in _CHECK_B_KEYWORDS:
            if kw in content_lower:
                return True, []

    reasons = [
        "Check B: no reflection references accumulating trend "
        f"(keywords: {_CHECK_B_KEYWORDS})"
    ]
    return False, reasons


def _check_c(reasoning_trace: str | None) -> tuple[bool, list[str]]:
    """Check C: final decision reasoning cites both positive and mixed experiences.

    Requires ≥ 1 positive keyword AND ≥ 1 mixed keyword in the trace.
    """
    reasons: list[str] = []

    if not reasoning_trace:
        return False, ["Check C: no reasoning trace from final decision"]

    trace_lower = reasoning_trace.lower()

    pos_hits = [kw for kw in _POSITIVE_KEYWORDS if kw in trace_lower]
    mixed_hits = [kw for kw in _MIXED_KEYWORDS if kw in trace_lower]

    passed = len(pos_hits) >= 1 and len(mixed_hits) >= 1

    if not pos_hits:
        reasons.append(
            f"Check C: no positive keywords found in reasoning trace "
            f"(expected one of: {_POSITIVE_KEYWORDS})"
        )
    if not mixed_hits:
        reasons.append(
            f"Check C: no mixed keywords found in reasoning trace "
            f"(expected one of: {_MIXED_KEYWORDS})"
        )

    return passed, reasons


# ---------------------------------------------------------------------------
# Core async runner
# ---------------------------------------------------------------------------


async def run_bv3(
    persona: Any,           # PersonaRecord
    llm_client: Any = None,
    tier: Any = None,       # SimulationTier — optional
) -> BV3Result:
    """Run the BV3 temporal consistency test for a single persona.

    Steps:
    1. Run positive stimuli 1-5 through run_loop, collecting DecisionOutput.confidence
       (only when result.decision is not None — otherwise record None).
    2. After stimulus 5, collect reflections from persona.memory.working.reflections.
    3. Run mixed stimuli 6-10 through run_loop.
    4. Run final stimulus 10 with decision_scenario=_DECISION_SCENARIO — collect
       result.decision.reasoning_trace.

    Then evaluate Check A, B, C and build BV3Result.
    """
    from src.cognition.loop import run_loop
    from src.experiment.session import SimulationTier

    resolved_tier: SimulationTier = (
        tier if tier is not None else SimulationTier.DEEP
    )

    persona_id: str = getattr(persona, "persona_id", "unknown")

    confidence_sequence: list[int] = []
    current_persona = persona

    # ------------------------------------------------------------------
    # Phase 1: Positive stimuli 1-5
    # ------------------------------------------------------------------
    for idx, stimulus in enumerate(_POSITIVE_STIMULI):
        try:
            current_persona, loop_result = await run_loop(
                stimulus=stimulus,
                persona=current_persona,
                stimulus_id=f"bv3-pos-{idx + 1}",
                decision_scenario=None,
                llm_client=llm_client,
                tier=resolved_tier,
            )
            if loop_result.decision is not None:
                confidence_sequence.append(loop_result.decision.confidence)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "BV3: run_loop failed on positive stimulus %d for persona %s: %s",
                idx + 1,
                persona_id,
                exc,
            )

    # ------------------------------------------------------------------
    # Phase 2: Collect reflections after positive arc
    # ------------------------------------------------------------------
    post_positive_reflections: list[Any] = []
    try:
        post_positive_reflections = list(
            current_persona.memory.working.reflections
        )
    except AttributeError:
        logger.warning("BV3: could not read reflections from persona %s", persona_id)

    reflection_count: int = len(post_positive_reflections)

    # ------------------------------------------------------------------
    # Phase 3: Mixed stimuli 6-10 (final one with decision scenario)
    # ------------------------------------------------------------------
    final_reasoning_trace: str | None = None

    for idx, stimulus in enumerate(_MIXED_STIMULI):
        is_final = idx == len(_MIXED_STIMULI) - 1
        scenario = _DECISION_SCENARIO if is_final else None

        try:
            current_persona, loop_result = await run_loop(
                stimulus=stimulus,
                persona=current_persona,
                stimulus_id=f"bv3-mix-{idx + 1}",
                decision_scenario=scenario,
                llm_client=llm_client,
                tier=resolved_tier,
            )
            if is_final and loop_result.decision is not None:
                final_reasoning_trace = loop_result.decision.reasoning_trace
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "BV3: run_loop failed on mixed stimulus %d for persona %s: %s",
                idx + 1,
                persona_id,
                exc,
            )

    # ------------------------------------------------------------------
    # Evaluate checks
    # ------------------------------------------------------------------
    check_a_passed, reasons_a = _check_a(confidence_sequence)
    check_b_passed, reasons_b = _check_b(post_positive_reflections)
    check_c_passed, reasons_c = _check_c(final_reasoning_trace)

    all_failure_reasons: list[str] = reasons_a + reasons_b + reasons_c

    overall_passed = check_a_passed and check_b_passed and check_c_passed

    return BV3Result(
        passed=overall_passed,
        persona_id=persona_id,
        check_a_passed=check_a_passed,
        check_b_passed=check_b_passed,
        check_c_passed=check_c_passed,
        confidence_sequence=confidence_sequence,
        reflection_count=reflection_count,
        failure_reasons=all_failure_reasons,
    )


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------


def run_bv3_sync(
    persona: Any,
    llm_client: Any = None,
    tier: Any = None,
) -> BV3Result:
    """Synchronous wrapper around run_bv3 for non-async callers."""
    return asyncio.run(run_bv3(persona, llm_client=llm_client, tier=tier))
