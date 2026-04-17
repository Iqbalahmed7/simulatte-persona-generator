"""BV5 — Resistance to Collapse Validator.

Master Spec §12 (Validation Framework):
  BV5: Resistance to collapse
    - Different decisions OR same decision with ≥3 different drivers
    - <50% verbatim overlap between persona responses
    - Tests that personas don't collapse into a single "modal" response

Validates that a cohort of personas given the same stimulus produce
meaningfully distinct responses — not identical copy-paste answers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BV5Result:
    """Result of BV5 collapse resistance test."""
    passed: bool
    cohort_size: int
    unique_decisions: int              # distinct decision categories
    driver_diversity: float            # mean Jaccard distance of key_drivers across pairs
    max_verbatim_overlap: float        # highest pairwise verbatim overlap (target: <0.50)
    failure_reasons: list[str] = field(default_factory=list)
    per_pair_details: list[dict] = field(default_factory=list)


def _tokenize(text: str) -> set[str]:
    """Extract lowercase word tokens (3+ chars) for overlap comparison."""
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def _jaccard_distance(set_a: set, set_b: set) -> float:
    """1 - Jaccard similarity. Returns 1.0 if both empty."""
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return 1.0 - (intersection / union) if union > 0 else 1.0


def _verbatim_overlap(text_a: str, text_b: str) -> float:
    """Compute word-level overlap ratio between two texts.

    Returns the fraction of shared tokens relative to the smaller text.
    This catches copy-paste responses even if they differ in length.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    shared = len(tokens_a & tokens_b)
    min_size = min(len(tokens_a), len(tokens_b))
    return shared / min_size


def run_bv5_check(
    responses: list[dict[str, Any]],
) -> BV5Result:
    """Run BV5 collapse resistance validation on a cohort's responses.

    Args:
        responses: List of dicts, each with:
            - persona_id: str
            - decision: str (the decision category)
            - key_drivers: list[str]
            - reasoning_trace: str (full reasoning text)

    Returns:
        BV5Result with pass/fail and diagnostics.
    """
    failure_reasons: list[str] = []
    n = len(responses)

    if n < 2:
        return BV5Result(
            passed=True, cohort_size=n, unique_decisions=n,
            driver_diversity=1.0, max_verbatim_overlap=0.0,
        )

    # -- Check 1: Decision diversity --
    decisions = [r.get("decision", "").strip().lower() for r in responses]
    unique_decisions = len(set(decisions))

    # If all same decision, check driver diversity
    all_same_decision = unique_decisions == 1

    # -- Check 2: Driver diversity (Jaccard distance) --
    driver_sets = [set(r.get("key_drivers", [])) for r in responses]
    pair_distances: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            dist = _jaccard_distance(driver_sets[i], driver_sets[j])
            pair_distances.append(dist)

    mean_driver_diversity = (
        sum(pair_distances) / len(pair_distances) if pair_distances else 0.0
    )

    if all_same_decision:
        # All same decision: need ≥3 unique drivers across the cohort
        all_drivers = set()
        for d_set in driver_sets:
            all_drivers.update(d_set)
        if len(all_drivers) < 3:
            failure_reasons.append(
                f"All personas chose '{decisions[0]}' with only {len(all_drivers)} "
                f"unique drivers (need ≥3)"
            )

    # -- Check 3: Verbatim overlap (<50%) --
    reasoning_texts = [r.get("reasoning_trace", "") for r in responses]
    max_overlap = 0.0
    per_pair_details: list[dict] = []

    for i in range(n):
        for j in range(i + 1, n):
            overlap = _verbatim_overlap(reasoning_texts[i], reasoning_texts[j])
            max_overlap = max(max_overlap, overlap)
            if overlap >= 0.40:  # flag pairs near threshold
                per_pair_details.append({
                    "persona_a": responses[i].get("persona_id", f"#{i}"),
                    "persona_b": responses[j].get("persona_id", f"#{j}"),
                    "verbatim_overlap": round(overlap, 3),
                    "same_decision": decisions[i] == decisions[j],
                })

    if max_overlap >= 0.50:
        failure_reasons.append(
            f"Max verbatim overlap: {max_overlap:.0%} (need <50%)"
        )

    passed = len(failure_reasons) == 0

    return BV5Result(
        passed=passed,
        cohort_size=n,
        unique_decisions=unique_decisions,
        driver_diversity=round(mean_driver_diversity, 3),
        max_verbatim_overlap=round(max_overlap, 3),
        failure_reasons=failure_reasons,
        per_pair_details=per_pair_details,
    )
