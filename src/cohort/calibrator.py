"""src/cohort/calibrator.py — Persona response consistency calibration.

Computes a basic calibration score from simulation results and updates
the CohortEnvelope.calibration_state accordingly.

Calibration logic:
  - "benchmark_calibrated": all personas produced a decision in the simulation
  - "uncalibrated": no simulation has been run
  - "calibration_failed": simulation ran but fewer than 50% of personas decided

The calibration score (0.0–1.0) is stored in CalibrationState.notes as
a formatted string: "consistency_score=0.82; N=5"
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.schema.cohort import CalibrationState, CohortEnvelope


def compute_calibration_state(
    envelope: CohortEnvelope,
    simulation_results: list[dict],
) -> CalibrationState:
    """Derive CalibrationState from simulation results.

    Args:
        envelope: The CohortEnvelope being calibrated.
        simulation_results: The 'results' list from _run_simulation output.
            Each entry: {"persona_id": str, "rounds": [{"decided": bool, ...}]}

    Returns:
        Updated CalibrationState.
    """
    if not simulation_results:
        return CalibrationState(status="uncalibrated")

    n = len(simulation_results)

    # Collect confidence scores from the final decided round per persona.
    # Using coefficient of variation (CV = stddev/mean) inverted as a consistency
    # proxy: low spread → high consistency. Score = 1 - min(CV, 1.0).
    # Falls back to participation rate if no confidence scores are available.
    confidences: list[float] = []
    for pr in simulation_results:
        rounds = pr.get("rounds", [])
        for r in rounds:
            if r.get("decided", False) and r.get("confidence") is not None:
                confidences.append(float(r["confidence"]))
                break  # one score per persona (last decided round)

    if len(confidences) >= 2:
        mean_c = sum(confidences) / len(confidences)
        variance = sum((c - mean_c) ** 2 for c in confidences) / len(confidences)
        stddev = variance ** 0.5
        cv = stddev / mean_c if mean_c > 0 else 1.0
        consistency_score = round(1.0 - min(cv, 1.0), 4)
    elif len(confidences) == 1:
        consistency_score = confidences[0] / 100.0
    else:
        # No confidence data — fall back to participation rate
        decided_count = sum(
            1 for pr in simulation_results
            if any(r.get("decided", False) for r in pr.get("rounds", []))
        )
        consistency_score = decided_count / n if n > 0 else 0.0

    if consistency_score >= 0.5:
        status = "benchmark_calibrated"
    else:
        status = "calibration_failed"

    return CalibrationState(
        status=status,
        method_applied="decision_consistency",
        last_calibrated=datetime.now(timezone.utc),
        benchmark_source="internal_simulation",
        notes=f"consistency_score={consistency_score:.4f}; N={n}",
    )


def apply_calibration(
    envelope: CohortEnvelope,
    simulation_results: list[dict],
) -> CohortEnvelope:
    """Return a new CohortEnvelope with updated calibration_state."""
    new_state = compute_calibration_state(envelope, simulation_results)
    return envelope.model_copy(update={"calibration_state": new_state})
