"""BV1 — Repeated-Run Behavioural Stability Validator.

Master Spec §12 (Validation Framework):
  BV1: Repeated-Run Behavioural Stability
    - Same persona + same stimulus sequence across 3 runs
    - ≥ 2 of 3 runs produce the same final decision
    - Reasoning traces share ≥ 60% of cited drivers
    - Confidence scores within ±15 points

Validates that a persona's identity produces stable-but-not-identical
behaviour across repeated runs. Complete randomness = no identity.
Perfect identity = no realism.

Usage
-----
This module is pure analysis — it does NOT orchestrate the 3 runs.
The caller is responsible for producing the 3 DecisionOutput captures
(typically by invoking src.cognition.decide.decide three times and
collecting the outputs into the format below).

The offline-analysis design makes BV1 composable with:
  - Pre-release validation harnesses (batch-call)
  - PQS pipeline (per-persona BV1 score contribution)
  - CI fixtures (replay saved captures)

BV1 Threshold (per spec)
------------------------
  decision_consistency ≥ 0.667  (2 of 3 runs identical decision)
  driver_overlap       ≥ 0.60   (60% of cited drivers appear in ≥2 runs)
  confidence_range     ≤ 30     (max − min ≤ 30 ≡ within ±15 of mean)

Determinism invariant (see src/cognition/decide.py _SITUATIONAL_MODIFIERS):
Same persona × same scenario always selects the same situational modifier,
so BV1 stability is a structural property of the cognitive loop — not a
probabilistic guarantee over LLM temperature. If BV1 fails, suspect either
(a) LLM temperature too high, or (b) non-deterministic inputs leaking in.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BV1Result:
    """Result of a BV1 repeated-run stability check."""
    passed: bool
    persona_id: str
    n_runs: int

    # Primary metrics
    decision_consistency: float          # fraction of runs producing the modal decision
    driver_overlap: float                # fraction of cited drivers appearing in ≥2 runs
    confidence_range: int                # max(confidence) − min(confidence)

    # Qualitative per-threshold pass flags
    decision_consistent: bool
    drivers_overlap_ok: bool
    confidence_stable: bool

    modal_decision: str = ""
    per_run_decisions: list[str] = field(default_factory=list)
    per_run_confidences: list[int] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)


def run_bv1_check(
    persona_id: str,
    runs: list[dict[str, Any]],
    decision_threshold: float = 0.667,   # ≥ 2/3 runs agree
    driver_overlap_threshold: float = 0.60,
    confidence_range_max: int = 30,      # max − min; ≤30 means within ±15 of centre
) -> BV1Result:
    """Run BV1 stability analysis over ≥2 captured runs of the same persona × scenario.

    Args:
        persona_id: Identifier for diagnostic traceability.
        runs: List of ≥2 capture dicts. Each must carry at least:
            - decision: str           (e.g. "purchase", "defer", "research_more")
            - confidence: int         (0-100)
            - key_drivers: list[str]  (top 2-3 cited factors)
          Additional keys are ignored.
        decision_threshold: Minimum fraction of runs agreeing on the modal decision.
            Default 0.667 ≡ 2 of 3 runs. For 2 runs, needs exact agreement.
        driver_overlap_threshold: Minimum fraction of cited drivers (union across runs)
            that appear in ≥2 runs. Default 0.60 per spec.
        confidence_range_max: Max permitted (max − min) of confidence across runs.
            Default 30 ≡ within ±15 of centre per spec.

    Returns:
        BV1Result with per-threshold pass flags + aggregate `passed`.
    """
    failure_reasons: list[str] = []
    n = len(runs)

    # Degenerate: fewer than 2 runs — stability is undefined. Pass with a warning.
    if n < 2:
        return BV1Result(
            passed=True,
            persona_id=persona_id,
            n_runs=n,
            decision_consistency=1.0,
            driver_overlap=1.0,
            confidence_range=0,
            decision_consistent=True,
            drivers_overlap_ok=True,
            confidence_stable=True,
            modal_decision=(runs[0].get("decision", "") if n == 1 else ""),
            per_run_decisions=[r.get("decision", "") for r in runs],
            per_run_confidences=[int(r.get("confidence", 0)) for r in runs],
            failure_reasons=["BV1 needs ≥2 runs to evaluate stability — skipped"],
        )

    # --- 1. Decision consistency ----------------------------------------
    decisions = [str(r.get("decision", "")).strip().lower() for r in runs]
    decision_counter = Counter(decisions)
    modal_decision, modal_count = decision_counter.most_common(1)[0]
    decision_consistency = modal_count / n
    decision_consistent = decision_consistency >= decision_threshold

    if not decision_consistent:
        failure_reasons.append(
            f"Decision consistency {decision_consistency:.0%} below threshold "
            f"{decision_threshold:.0%} (modal='{modal_decision}' in {modal_count}/{n} runs)"
        )

    # --- 2. Driver overlap ----------------------------------------------
    # Count how often each driver appears across all runs.
    driver_appearances: Counter = Counter()
    for run in runs:
        # De-duplicate drivers within a single run (a driver counted once per run).
        drivers_in_run = {str(d).strip().lower() for d in run.get("key_drivers", []) if d}
        for d in drivers_in_run:
            driver_appearances[d] += 1

    if driver_appearances:
        total_unique = len(driver_appearances)
        consistent_drivers = sum(1 for count in driver_appearances.values() if count >= 2)
        driver_overlap = consistent_drivers / total_unique
    else:
        # No drivers cited anywhere — can't assess overlap, treat as failure.
        driver_overlap = 0.0

    drivers_overlap_ok = driver_overlap >= driver_overlap_threshold
    if not drivers_overlap_ok:
        failure_reasons.append(
            f"Driver overlap {driver_overlap:.0%} below threshold "
            f"{driver_overlap_threshold:.0%} "
            f"({sum(1 for c in driver_appearances.values() if c >= 2)} of "
            f"{len(driver_appearances)} unique drivers appear in ≥2 runs)"
        )

    # --- 3. Confidence stability ----------------------------------------
    confidences = [int(r.get("confidence", 0)) for r in runs]
    confidence_range = max(confidences) - min(confidences) if confidences else 0
    confidence_stable = confidence_range <= confidence_range_max
    if not confidence_stable:
        failure_reasons.append(
            f"Confidence range {confidence_range} exceeds max {confidence_range_max} "
            f"(min={min(confidences)}, max={max(confidences)})"
        )

    passed = decision_consistent and drivers_overlap_ok and confidence_stable

    return BV1Result(
        passed=passed,
        persona_id=persona_id,
        n_runs=n,
        decision_consistency=round(decision_consistency, 3),
        driver_overlap=round(driver_overlap, 3),
        confidence_range=confidence_range,
        decision_consistent=decision_consistent,
        drivers_overlap_ok=drivers_overlap_ok,
        confidence_stable=confidence_stable,
        modal_decision=modal_decision,
        per_run_decisions=decisions,
        per_run_confidences=confidences,
        failure_reasons=failure_reasons,
    )
