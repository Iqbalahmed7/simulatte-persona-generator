"""src/calibration/engine.py

Orchestrates calibration of a CohortEnvelope against benchmarks or client outcome data.

Two methods:
  run_benchmark_calibration — compares simulation outputs vs domain benchmarks
  run_feedback_calibration  — adjusts persona tendencies from real outcome data

Both update cohort.calibration_state and return an updated CohortEnvelope.
Spec ref: Validity Protocol Module 4 (C1-C5), Master Spec §7 grounding/calibration.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.schema.cohort import CalibrationState, CohortEnvelope

logger = logging.getLogger(__name__)


class CalibrationEngine:
    """Orchestrates benchmark and client-feedback calibration for a CohortEnvelope."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_benchmark_calibration(
        self,
        cohort: CohortEnvelope,
        benchmarks: dict,
        # benchmarks keys:
        #   "conversion_rate" (float 0-1)   — required
        #   "wtp_median"      (float)        — required
        #   "wtp_mean"        (float)        — optional
        #   "top_driver"      (str)          — optional
    ) -> CohortEnvelope:
        """Compare cohort simulation outputs vs domain benchmarks.

        Computes a proxy simulated-conversion rate from persona attributes,
        runs the C3 plausibility gate, builds a new CalibrationState, and
        returns an updated CohortEnvelope via model_copy (never mutates input).

        Args:
            cohort: The CohortEnvelope to calibrate.
            benchmarks: Dict of domain benchmark values.

        Returns:
            Updated CohortEnvelope with calibration_state.status == "benchmark_calibrated".
        """
        from src.calibration.population_validator import check_c3

        if not cohort.personas:
            logger.warning(
                "run_benchmark_calibration: cohort %s has no personas; returning unchanged.",
                cohort.cohort_id,
            )
            new_state = CalibrationState(
                status="calibration_failed",
                method_applied="benchmark_anchoring",
                last_calibrated=datetime.now(tz=timezone.utc),
                benchmark_source=(
                    f"conversion={benchmarks.get('conversion_rate')}, "
                    f"wtp_median={benchmarks.get('wtp_median')}"
                ),
                notes="Benchmark anchoring failed: cohort has no personas.",
            )
            return cohort.model_copy(update={"calibration_state": new_state})

        # Step 2 — Compute simulated_conversion proxy.
        # Uses risk_appetite as a proxy for purchase readiness:
        # personas with medium or high risk_appetite are counted as likely converters.
        simulated_conversion = len(
            [
                p
                for p in cohort.personas
                if p.derived_insights.risk_appetite in ("medium", "high")
            ]
        ) / len(cohort.personas)

        # Step 3 — Run C3 gate.
        benchmark_conversion = benchmarks.get("conversion_rate", 0.5)
        c3 = check_c3(simulated_conversion, benchmark_conversion)

        if not c3.passed:
            logger.warning(
                "run_benchmark_calibration: C3 gate WARN for cohort %s. %s",
                cohort.cohort_id,
                c3.message,
            )
        else:
            logger.info(
                "run_benchmark_calibration: C3 gate PASS for cohort %s. %s",
                cohort.cohort_id,
                c3.message,
            )

        # Step 4 — Build new CalibrationState.
        new_state = CalibrationState(
            status="benchmark_calibrated",
            method_applied="benchmark_anchoring",
            last_calibrated=datetime.now(tz=timezone.utc),
            benchmark_source=(
                f"conversion={benchmarks.get('conversion_rate')}, "
                f"wtp_median={benchmarks.get('wtp_median')}"
            ),
            notes=(
                f"Benchmark anchoring applied. "
                f"Simulated conversion proxy: {simulated_conversion:.2%}. "
                f"C3 gate: {'PASS' if c3.passed else 'WARN'}."
            ),
        )

        # Step 5 — Return updated cohort (immutable model_copy pattern).
        return cohort.model_copy(update={"calibration_state": new_state})

    def run_feedback_calibration(
        self,
        cohort: CohortEnvelope,
        outcomes: list[dict],
        # outcomes items: {"persona_id": str, "actual_outcome": str, "channel": str}
        # actual_outcome values: "purchased", "deferred", "rejected", "researched"
    ) -> CohortEnvelope:
        """Adjust cohort calibration state from real client outcome data.

        For each outcome record, finds the matching persona by persona_id and
        calls adjust_tendency_from_outcome to update its tendency bands.
        Returns an updated CohortEnvelope via model_copy (never mutates input).

        Args:
            cohort: The CohortEnvelope to update.
            outcomes: List of real outcome dicts from client data.

        Returns:
            Updated CohortEnvelope with calibration_state.status == "client_calibrated"
            and updated persona tendency bands where outcome data was matched.
        """
        from src.calibration.feedback_loop import adjust_tendency_from_outcome

        # Step 2 & 3 — Build a persona_id → index map, then update matched personas.
        persona_map: dict[str, int] = {
            p.persona_id: i for i, p in enumerate(cohort.personas)
        }
        updated_personas = list(cohort.personas)  # shallow copy; personas are immutable models

        matched = 0
        for outcome in outcomes:
            pid = outcome.get("persona_id")
            if pid is None:
                logger.warning(
                    "run_feedback_calibration: outcome record missing persona_id; skipping. %r",
                    outcome,
                )
                continue

            idx = persona_map.get(pid)
            if idx is None:
                logger.warning(
                    "run_feedback_calibration: persona_id=%r not found in cohort %s; skipping.",
                    pid,
                    cohort.cohort_id,
                )
                continue

            # Step 3 — Apply tendency adjustment.
            updated_persona = adjust_tendency_from_outcome(updated_personas[idx], outcome)
            updated_personas[idx] = updated_persona
            matched += 1

        if matched < len(outcomes):
            logger.info(
                "run_feedback_calibration: %d/%d outcome records matched to personas in cohort %s.",
                matched,
                len(outcomes),
                cohort.cohort_id,
            )

        # Step 5 — Build new CalibrationState.
        new_state = CalibrationState(
            status="client_calibrated",
            method_applied="client_feedback_loop",
            last_calibrated=datetime.now(tz=timezone.utc),
            benchmark_source=None,
            notes=(
                f"Client feedback loop applied. "
                f"{len(outcomes)} outcome records processed."
            ),
        )

        # Step 6 — Return updated cohort (immutable model_copy pattern).
        return cohort.model_copy(
            update={"personas": updated_personas, "calibration_state": new_state}
        )
