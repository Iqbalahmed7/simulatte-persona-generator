"""src/validation/bv6_override.py — BV6 Override Scenario Test Runner.

Sprint 21 — Codex (Simulation Quality Gates)

Spec: Validity Protocol Module 2 — BV6 (Believable Consistency vs Unrealistic Rigidity)

BV6 tests that a persona is consistent with its identity but not robotically so.
Presents 10 scenarios (8 normal + 2 override) and checks:
  (a) 70–90% tendency-consistent in the 8 normal scenarios
  (b) ≥ 1 of 2 override scenarios produces a departure with explicit reasoning
  (c) persona does not show 100% consistency across all 10 scenarios

FAIL conditions:
  - Perfect 100% consistency across all 10 (robot, not person)
  - Random departures in 5+ normal scenarios without override context (no identity)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from src.schema.persona import PersonaRecord
from src.experiment.session import SimulationTier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

_NORMAL_SCENARIOS = [
    "Nutrimix is on sale for ₹599 this week. Should you buy?",
    "Your sister bought Nutrimix last month and her daughter loves it. Should you try it?",
    "There is a new competitor product called KidBoost at ₹549. Should you switch?",
    "Your subscription is due for renewal at ₹649. Should you continue?",
    "A pediatric dietitian at your clinic recommends Nutrimix. Should you start?",
    "Nutrimix releases a chocolate flavour. Should you try it?",
    "BigBasket is offering 10% cashback on Nutrimix today only. Should you buy?",
    "Your child's teacher mentions other kids in class take Nutrimix. Should you buy?",
]

_OVERRIDE_SCENARIOS = [
    # Override 1: health emergency forces price-sensitive persona to ignore cost
    (
        "Your child is severely underweight. The paediatrician says malnutrition is a "
        "serious risk and specifically prescribes Nutrimix daily for 3 months at "
        "₹799/month. Should you buy despite the cost?"
    ),
    # Override 2: clear product failure forces brand-loyal persona to reconsider
    (
        "You have been giving your child Nutrimix for 6 months. Their last two blood "
        "tests show no improvement in iron or calcium levels. The doctor says the "
        "supplement is not working for your child. Should you continue?"
    ),
]

_DECISION_SUFFIX = " Explain your reasoning in detail."

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class BV6Result:
    """Result of a BV6 override scenario test run for a single persona."""

    passed: bool
    persona_id: str
    check_a_passed: bool    # 70–90% tendency-consistent across 8 normal scenarios
    check_b_passed: bool    # ≥ 1 override departure with explicit reasoning
    check_c_passed: bool    # not 100% consistent across all 10 scenarios
    consistency_rate: float  # 0.0–1.0, computed over 8 normal scenarios only
    override_departures: int  # 0, 1, or 2
    failure_reasons: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable one-paragraph summary of this BV6 result."""
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"BV6 {status} — persona_id={self.persona_id}",
            f"  Consistency rate (8 normal scenarios): {self.consistency_rate:.0%}",
            f"  Override departures (max 2): {self.override_departures}",
            f"  Check A (70–90% consistent): {'PASS' if self.check_a_passed else 'FAIL'}",
            f"  Check B (≥1 override departure with reasoning): {'PASS' if self.check_b_passed else 'FAIL'}",
            f"  Check C (not 100% consistent): {'PASS' if self.check_c_passed else 'FAIL'}",
        ]
        if self.failure_reasons:
            lines.append("  Failure reasons:")
            for reason in self.failure_reasons:
                lines.append(f"    - {reason}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tendency determination
# ---------------------------------------------------------------------------


def _determine_tendency(persona: PersonaRecord) -> str:
    """Derive the persona's PRIMARY decision tendency from derived_insights.

    Rules (in priority order):
      1. risk_appetite == "low"        → "avoid risk / prefer familiar"
      2. decision_style == "habitual"  → "stick with known brand"
      3. else                          → "analytical / research-first"
    """
    insights = persona.derived_insights
    if insights.risk_appetite == "low":
        return "avoid risk / prefer familiar"
    if insights.decision_style == "habitual":
        return "stick with known brand"
    return "analytical / research-first"


# ---------------------------------------------------------------------------
# Consistency check per scenario
# ---------------------------------------------------------------------------


def _is_tendency_consistent(decision_text: str, tendency: str) -> bool:
    """Return True if a decision is consistent with the persona's tendency.

    For 'low risk / prefer familiar' personas:
      Consistent = decision is "buy" or "research_more" (not "reject" or "switch").
    For 'habitual / stick with known brand' personas:
      Consistent = decision is "buy" or "trial" (not "reject").
    For 'analytical / research-first' personas:
      Any decision is consistent — they reason their way to either outcome.
    """
    d = decision_text.lower().strip()

    if tendency == "avoid risk / prefer familiar":
        # Inconsistent if the persona firmly rejects or switches away
        return not (d.startswith("reject") or d.startswith("switch") or d == "no")

    if tendency == "stick with known brand":
        # Inconsistent only if outright rejection
        return not d.startswith("reject")

    # "analytical / research-first" — any decision is consistent
    return True


# ---------------------------------------------------------------------------
# Override departure check
# ---------------------------------------------------------------------------


def _is_override_departure(
    override_index: int,
    decision_text: str,
    reasoning_trace: str,
    tendency: str,
) -> bool:
    """Return True if an override scenario produced a qualifying departure.

    Override 1 (health emergency, index 0):
      Departure = decision is "buy" AND the reasoning trace mentions price/cost
      (demonstrates the persona consciously overrode their cost sensitivity).
      Reasoning trace must be > 100 chars.

    Override 2 (product failure, index 1):
      Departure = decision is NOT "buy" (i.e. research_more, defer, or reject).
      Reasoning trace must be > 100 chars.

    In both cases, the reasoning trace length > 100 chars requirement ensures
    there is explicit cited reasoning rather than a one-liner.
    """
    d = decision_text.lower().strip()
    trace = reasoning_trace.lower()
    trace_len = len(reasoning_trace.strip())

    if trace_len <= 100:
        # No explicit reasoning — not a qualifying departure
        return False

    if override_index == 0:
        # Health emergency: persona buys despite being price-sensitive
        mentions_cost = "price" in trace or "cost" in trace or "₹" in trace or "expensive" in trace
        return d.startswith("buy") or d.startswith("yes") and mentions_cost

    if override_index == 1:
        # Product failure: persona does NOT continue buying
        is_not_buy = not (d.startswith("buy") or d.startswith("yes"))
        return is_not_buy

    return False


# ---------------------------------------------------------------------------
# Core async runner
# ---------------------------------------------------------------------------


async def run_bv6(
    persona: PersonaRecord,
    llm_client: Any = None,
    tier: SimulationTier | None = None,
) -> BV6Result:
    """Run the BV6 override scenario test for a single persona.

    Presents 10 scenarios (8 normal + 2 override) via run_loop with
    decision_scenario set to the scenario text + reasoning suffix.
    Evaluates the three BV6 checks and returns a BV6Result.

    Parameters
    ----------
    persona : PersonaRecord
        The fully-assembled persona to test. Working memory is used as-is;
        callers should reset working memory before calling if desired.
    llm_client : optional
        Injected LLM client for testing. Passed through to run_loop.
    tier : SimulationTier, optional
        Simulation tier for model routing. Defaults to SimulationTier.DEEP.
    """
    # Import here to avoid circular imports at module load
    from src.cognition.loop import run_loop

    _tier = tier if tier is not None else SimulationTier.DEEP
    tendency = _determine_tendency(persona)

    logger.info(
        "BV6 starting: persona_id=%s, tendency=%s, tier=%s",
        persona.persona_id, tendency, _tier.value,
    )

    # --------------------------------------------------------------------------
    # Run all 10 scenarios
    # --------------------------------------------------------------------------
    all_scenarios = _NORMAL_SCENARIOS + _OVERRIDE_SCENARIOS
    decisions: list[str] = []
    reasoning_traces: list[str] = []

    current_persona = persona
    for idx, scenario_text in enumerate(all_scenarios):
        full_scenario = scenario_text + _DECISION_SUFFIX
        # Use scenario text itself as the perceive stimulus too (lightweight)
        updated_persona, loop_result = await run_loop(
            stimulus=scenario_text,
            persona=current_persona,
            stimulus_id=f"bv6-s{idx:02d}",
            decision_scenario=full_scenario,
            llm_client=llm_client,
            tier=_tier,
        )
        current_persona = updated_persona

        if loop_result.decision is not None:
            decisions.append(loop_result.decision.decision)
            reasoning_traces.append(loop_result.decision.reasoning_trace)
        else:
            # No decision returned — treat as None/empty
            decisions.append("")
            reasoning_traces.append("")
            logger.warning(
                "BV6: no decision returned for scenario %d (persona=%s)",
                idx, persona.persona_id,
            )

    # --------------------------------------------------------------------------
    # Check A — consistency rate across 8 normal scenarios
    # --------------------------------------------------------------------------
    normal_decisions = decisions[:8]
    normal_consistent_count = sum(
        1 for d in normal_decisions if _is_tendency_consistent(d, tendency)
    )
    consistency_rate = normal_consistent_count / 8 if normal_decisions else 0.0
    check_a_passed = 0.70 <= consistency_rate <= 0.90

    # --------------------------------------------------------------------------
    # Check B — ≥ 1 override departure with explicit reasoning
    # --------------------------------------------------------------------------
    override_decisions = decisions[8:]
    override_traces = reasoning_traces[8:]
    override_departures = 0

    for i, (dec, trace) in enumerate(zip(override_decisions, override_traces)):
        if _is_override_departure(i, dec, trace, tendency):
            override_departures += 1

    check_b_passed = override_departures >= 1

    # --------------------------------------------------------------------------
    # Check C — not 100% consistent across all 10 scenarios
    # --------------------------------------------------------------------------
    all_consistent_count = sum(
        1 for d in decisions if _is_tendency_consistent(d, tendency)
    )
    check_c_passed = all_consistent_count < len(decisions)

    # --------------------------------------------------------------------------
    # Determine pass/fail and collect failure reasons
    # --------------------------------------------------------------------------
    failure_reasons: list[str] = []

    if not check_a_passed:
        if consistency_rate > 0.90:
            failure_reasons.append(
                f"Consistency rate {consistency_rate:.0%} exceeds 90% ceiling — "
                "persona is too rigidly consistent across normal scenarios."
            )
        else:
            failure_reasons.append(
                f"Consistency rate {consistency_rate:.0%} is below 70% floor — "
                "persona shows insufficient identity coherence across normal scenarios."
            )

    if not check_b_passed:
        failure_reasons.append(
            "No override scenario produced a qualifying departure with explicit reasoning "
            "(≥ 1 required). Persona may be robotically applying tendency even under "
            "compelling override conditions."
        )

    if not check_c_passed:
        failure_reasons.append(
            "Persona showed 100% tendency-consistency across all 10 scenarios including "
            "overrides. Perfect consistency = robot, not person."
        )

    passed = check_a_passed and check_b_passed and check_c_passed

    result = BV6Result(
        passed=passed,
        persona_id=persona.persona_id,
        check_a_passed=check_a_passed,
        check_b_passed=check_b_passed,
        check_c_passed=check_c_passed,
        consistency_rate=consistency_rate,
        override_departures=override_departures,
        failure_reasons=failure_reasons,
    )

    logger.info(
        "BV6 complete: persona_id=%s, passed=%s, consistency_rate=%.2f, "
        "override_departures=%d",
        persona.persona_id, passed, consistency_rate, override_departures,
    )

    return result


# ---------------------------------------------------------------------------
# Synchronous wrapper for CLI / non-async callers
# ---------------------------------------------------------------------------


def run_bv6_sync(
    persona: PersonaRecord,
    llm_client: Any = None,
    tier: SimulationTier | None = None,
) -> BV6Result:
    """Synchronous wrapper around run_bv6.

    Creates a new event loop if none is running.
    Callers already inside an async context should use ``await run_bv6(...)``
    directly.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Inside an already-running loop (e.g. Jupyter) — cannot use run_until_complete.
            # Raise a clear error directing the caller to use the async version.
            raise RuntimeError(
                "run_bv6_sync() called from within a running event loop. "
                "Use 'await run_bv6(persona, ...)' instead."
            )
        return loop.run_until_complete(run_bv6(persona, llm_client=llm_client, tier=tier))
    except RuntimeError as exc:
        if "no current event loop" in str(exc).lower():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(run_bv6(persona, llm_client=llm_client, tier=tier))
            finally:
                loop.close()
        raise
