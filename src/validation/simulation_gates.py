"""src/validation/simulation_gates.py — S1–S4 simulation quality gates.

Sprint 21 — Goose
Validity Protocol: Module 3 (Simulation Quality Gates)

Wraps the four simulation quality gates from SIMULATTE_VALIDITY_PROTOCOL.md
as callable, deterministic, no-LLM functions.

Gates:
    S1  Zero error rate         — all sample personas completed without error
    S2  Decision diversity      — no single decision option > 90% of cohort
    S3  Driver coherence        — top drivers are category-relevant
    S4  WTP plausibility        — median WTP within ±30% of ask price

Usage:
    from src.validation.simulation_gates import (
        GateResult, check_s1, check_s2, check_s3, check_s4, run_all_gates
    )
    result = check_s2(decisions)
    if not result.passed and not result.warning:
        raise RuntimeError(result.action_required)
"""
from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GateResult:
    """Result of a single simulation quality gate check."""

    gate: str                       # "S1", "S2", "S3", "S4"
    passed: bool
    threshold: str                  # human-readable threshold
    actual: str                     # human-readable actual value
    action_required: str | None     # what to do on failure (None if passed)
    warning: bool = False           # True = warn but don't block


# ---------------------------------------------------------------------------
# S1 — Zero error rate
# ---------------------------------------------------------------------------

def check_s1(personas: list, sample_size: int = 5) -> GateResult:
    """S1: Run --max 5 first; all 5 must complete without error.

    Args:
        personas: List of PersonaRecord objects that have been through the
                  pipeline.  Each persona must have a valid
                  memory.working.simulation_state (no None, no error markers).
        sample_size: Minimum number of personas required (default 5).

    Returns:
        GateResult for S1.
    """
    _ERROR_MARKERS = {"error", "failed", "invalid", "exception", "none"}

    validation_errors: list[str] = []

    for persona in personas:
        # Accept both attribute-style (PersonaRecord) and dict-style objects
        try:
            sim_state = persona.memory.working.simulation_state
        except AttributeError:
            # Fallback: dict-like access
            try:
                sim_state = (
                    persona["memory"]["working"]["simulation_state"]
                )
            except (KeyError, TypeError):
                sim_state = None

        if sim_state is None:
            validation_errors.append(
                getattr(persona, "persona_id", str(persona))
            )
        elif isinstance(sim_state, str) and sim_state.lower() in _ERROR_MARKERS:
            validation_errors.append(
                getattr(persona, "persona_id", str(persona))
            )

    loaded = len(personas)
    actual_str = f"{loaded} personas loaded successfully"

    passed = loaded >= sample_size and len(validation_errors) == 0

    return GateResult(
        gate="S1",
        passed=passed,
        threshold=f"All {sample_size} sample personas must complete without error",
        actual=actual_str,
        action_required=(
            None if passed else "Debug pipeline before running full population"
        ),
    )


# ---------------------------------------------------------------------------
# S2 — Decision diversity
# ---------------------------------------------------------------------------

def check_s2(decisions: list[str]) -> GateResult:
    """S2: No single decision option > 90% of cohort.

    Args:
        decisions: List of decision strings
                   (e.g. ["buy", "buy", "defer", "research_more", ...]).

    Returns:
        GateResult for S2.
    """
    if not decisions:
        return GateResult(
            gate="S2",
            passed=True,
            threshold="No single option > 90%",
            actual="No decisions provided",
            action_required=None,
            warning=True,
        )

    counts = Counter(decisions)
    total = len(decisions)
    dominant_decision, dominant_count = counts.most_common(1)[0]
    max_pct = dominant_count / total * 100

    actual_str = f"Max: '{dominant_decision}' at {max_pct:.1f}%"

    if max_pct <= 80.0:
        passed = True
        warning = False
        action = None
    elif max_pct <= 90.0:
        # Warn but don't fail
        passed = True
        warning = True
        action = "Review stimulus design; may indicate broken persona or prompt issue"
    else:
        passed = False
        warning = False
        action = "Review stimulus design; may indicate broken persona or prompt issue"

    return GateResult(
        gate="S2",
        passed=passed,
        threshold="No single option > 90%",
        actual=actual_str,
        action_required=action,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# S3 — Driver coherence
# ---------------------------------------------------------------------------

def check_s3(
    key_drivers: list[list[str]],
    domain_keywords: list[str],
) -> GateResult:
    """S3: Top decision drivers are category-relevant.

    Args:
        key_drivers: List of key_driver lists from DecisionOutput.
        domain_keywords: Relevant terms for this domain (case-insensitive match).

    Returns:
        GateResult for S3.
    """
    if not domain_keywords:
        return GateResult(
            gate="S3",
            passed=True,
            threshold=">= 70% of driver lists contain category-relevant terms",
            actual="No domain keywords provided",
            action_required=None,
            warning=True,
        )

    if not key_drivers:
        return GateResult(
            gate="S3",
            passed=True,
            threshold=">= 70% of driver lists contain category-relevant terms",
            actual="No driver lists provided",
            action_required=None,
            warning=True,
        )

    lower_keywords = {kw.lower() for kw in domain_keywords}

    non_empty = [dl for dl in key_drivers if dl]
    if not non_empty:
        return GateResult(
            gate="S3",
            passed=False,
            threshold=">= 70% of driver lists contain category-relevant terms",
            actual="0.0% of driver lists contain domain keywords",
            action_required="Review stimulus prompts; check tendency-attribute assignment",
        )

    relevant_count = 0
    for driver_list in non_empty:
        for driver in driver_list:
            if any(kw in driver.lower() for kw in lower_keywords):
                relevant_count += 1
                break  # one match per driver list is sufficient

    relevance_pct = relevant_count / len(non_empty) * 100
    actual_str = f"{relevance_pct:.1f}% of driver lists contain domain keywords"
    passed = relevance_pct >= 70.0

    return GateResult(
        gate="S3",
        passed=passed,
        threshold=">= 70% of driver lists contain category-relevant terms",
        actual=actual_str,
        action_required=(
            None if passed
            else "Review stimulus prompts; check tendency-attribute assignment"
        ),
    )


# ---------------------------------------------------------------------------
# S4 — WTP plausibility
# ---------------------------------------------------------------------------

def check_s4(wtp_values: list[float], ask_price: float) -> GateResult:
    """S4: Median WTP within ±30% of ask price.

    Args:
        wtp_values: List of WTP floats.  0.0 and None are skipped.
        ask_price: The reference ask price (must be > 0).

    Returns:
        GateResult for S4.
    """
    threshold_str = f"Median WTP within ±30% of ask price (₹{ask_price:.0f})"

    # Filter out zeros and None
    valid_wtp = [v for v in wtp_values if v is not None and v != 0.0]

    if not valid_wtp:
        return GateResult(
            gate="S4",
            passed=True,
            threshold=threshold_str,
            actual="No WTP data",
            action_required=None,
            warning=True,
        )

    median_wtp = statistics.median(valid_wtp)
    deviation = abs(median_wtp - ask_price) / ask_price
    actual_str = f"Median WTP: ₹{median_wtp:.0f} ({deviation * 100:.1f}% from ask)"

    if deviation <= 0.20:
        passed = True
        warning = False
        action = None
    elif deviation <= 0.30:
        # Warn but don't fail
        passed = True
        warning = True
        action = "Check tendency-attribute proxy formulas; may need recalibration"
    else:
        passed = False
        warning = False
        action = "Check tendency-attribute proxy formulas; may need recalibration"

    return GateResult(
        gate="S4",
        passed=passed,
        threshold=threshold_str,
        actual=actual_str,
        action_required=action,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

def run_all_gates(
    personas: list,
    decisions: list[str],
    key_drivers: list[list[str]],
    wtp_values: list[float],
    ask_price: float,
    domain_keywords: list[str] | None = None,
) -> list[GateResult]:
    """Run S1–S4 and return all four results.

    Args:
        personas: List of PersonaRecord objects (for S1).
        decisions: List of decision strings (for S2).
        key_drivers: List of key_driver lists (for S3).
        wtp_values: List of WTP floats (for S4).
        ask_price: Reference ask price (for S4).
        domain_keywords: Category-relevant terms for S3 (default: empty list).

    Returns:
        List of four GateResult objects in order [S1, S2, S3, S4].
    """
    if domain_keywords is None:
        domain_keywords = []

    return [
        check_s1(personas),
        check_s2(decisions),
        check_s3(key_drivers, domain_keywords),
        check_s4(wtp_values, ask_price),
    ]
