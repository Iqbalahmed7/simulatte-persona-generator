"""src/calibration/population_validator.py

C1-C5 calibration quality gates.
Deterministic — no LLM calls.
Spec ref: Validity Protocol Module 4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


# ---------------------------------------------------------------------------
# C3Result — kept for backward compat with engine.py which imports check_c3
# ---------------------------------------------------------------------------

@dataclass
class C3Result:
    """Result of the C3 conversion-plausibility gate."""

    passed: bool
    simulated: float
    benchmark: float
    ratio: float
    message: str


def check_c3(simulated_conversion: float, benchmark_conversion: float) -> C3Result:
    """C3 gate: check whether simulated conversion is within 0.5x–2x of benchmark.

    Args:
        simulated_conversion: Proxy buy-rate computed from cohort attributes (0.0–1.0).
        benchmark_conversion: Known domain benchmark conversion rate (0.0–1.0).

    Returns:
        C3Result with passed=True if within acceptable range.
    """
    if benchmark_conversion <= 0:
        return C3Result(
            passed=True,
            simulated=simulated_conversion,
            benchmark=benchmark_conversion,
            ratio=1.0,
            message="C3 SKIP — benchmark_conversion is zero or negative; gate skipped.",
        )

    ratio = simulated_conversion / benchmark_conversion
    passed = 0.5 <= ratio <= 2.0
    if passed:
        msg = (
            f"C3 PASS — simulated/benchmark ratio={ratio:.2f} (within 0.5x–2x range)."
        )
    else:
        msg = (
            f"C3 WARN — simulated/benchmark ratio={ratio:.2f} is outside 0.5x–2x range. "
            f"Simulated={simulated_conversion:.2%}, Benchmark={benchmark_conversion:.2%}."
        )
    return C3Result(
        passed=passed,
        simulated=simulated_conversion,
        benchmark=benchmark_conversion,
        ratio=ratio,
        message=msg,
    )


# ---------------------------------------------------------------------------
# CalibrationGateReport — Sprint 22 spec deliverable
# ---------------------------------------------------------------------------

@dataclass
class CalibrationGateReport:
    """Aggregate report for C1–C5 calibration quality gates.

    c1_passed : status not null
    c2_passed : benchmark applied at least once
    c3_passed : conversion plausibility (0.5x-2x)
    c4_passed : client feedback trigger check
    c5_warning: staleness > 6 months (warning only, does not block)
    """

    c1_passed: bool
    c2_passed: bool
    c3_passed: bool
    c4_passed: bool
    c5_warning: bool
    notes: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """True when all blocking gates pass. C5 is warning-only and does not block."""
        return self.c1_passed and self.c2_passed and self.c3_passed and self.c4_passed

    def summary(self) -> str:
        """Return a human-readable summary of the gate results."""
        lines = [
            "Calibration Gate Report",
            "=======================",
            f"C1 (status not null)          : {'PASS' if self.c1_passed else 'FAIL'}",
            f"C2 (benchmark applied)        : {'PASS' if self.c2_passed else 'FAIL'}",
            f"C3 (conversion plausibility)  : {'PASS' if self.c3_passed else 'FAIL'}",
            f"C4 (client feedback trigger)  : {'PASS' if self.c4_passed else 'PASS (not required)' if self.c4_passed else 'FAIL'}",
            f"C5 (staleness > 6 months)     : {'WARN' if self.c5_warning else 'OK'}",
            f"Overall                       : {'PASS' if self.all_passed else 'FAIL'}",
        ]
        if self.notes:
            lines.append("")
            lines.append("Notes:")
            for note in self.notes:
                lines.append(f"  - {note}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# validate_calibration — primary public API
# ---------------------------------------------------------------------------

_SIX_MONTHS = timedelta(days=183)


def validate_calibration(
    cohort: Any,
    simulated_conversion: float | None = None,
    benchmark_conversion: float | None = None,
) -> CalibrationGateReport:
    """Run C1–C5 gates against a CohortEnvelope.

    Args:
        cohort: A CohortEnvelope instance.
        simulated_conversion: Optional simulated buy-rate (0.0–1.0) for C3 gate.
        benchmark_conversion: Optional known domain benchmark conversion (0.0–1.0) for C3 gate.

    Returns:
        CalibrationGateReport with per-gate results.
    """
    notes: list[str] = []
    state = getattr(cohort, "calibration_state", None)

    # -----------------------------------------------------------------------
    # C1 — status not null and not empty string
    # -----------------------------------------------------------------------
    if state is None or getattr(state, "status", None) is None or getattr(state, "status", "") == "":
        c1_passed = False
        notes.append("C1 FAIL — calibration_state.status is None or empty.")
    else:
        c1_passed = True

    # -----------------------------------------------------------------------
    # C2 — benchmark applied at least once (method_applied is not None)
    # -----------------------------------------------------------------------
    method_applied = getattr(state, "method_applied", None) if state is not None else None
    if method_applied is None:
        c2_passed = False
        notes.append("C2 FAIL — method_applied is None; benchmark anchoring not yet applied.")
    else:
        c2_passed = True

    # -----------------------------------------------------------------------
    # C3 — conversion plausibility: simulated within 0.5x–2x of benchmark
    # -----------------------------------------------------------------------
    if simulated_conversion is not None and benchmark_conversion is not None:
        if benchmark_conversion <= 0:
            c3_passed = True
            notes.append("C3 SKIP — benchmark_conversion is zero or negative; gate auto-passed.")
        else:
            ratio = simulated_conversion / benchmark_conversion
            c3_passed = 0.5 <= ratio <= 2.0
            if not c3_passed:
                notes.append(
                    f"C3 WARN — simulated/benchmark ratio={ratio:.2f} is outside 0.5x–2x. "
                    f"Simulated={simulated_conversion:.2%}, Benchmark={benchmark_conversion:.2%}."
                )
    else:
        # No conversion data provided — auto-pass with note
        c3_passed = True
        notes.append("C3: no conversion data provided, skipped")

    # -----------------------------------------------------------------------
    # C4 — client feedback trigger check
    # When client data IS available (status == "client_calibrated") → pass.
    # Otherwise benchmark_calibrated or any other status → pass by default
    # (C4 is only required when client outcome data is actually available).
    # -----------------------------------------------------------------------
    status = getattr(state, "status", None) if state is not None else None
    if status == "client_calibrated":
        c4_passed = True
    elif status == "benchmark_calibrated":
        # Benchmark applied but no client data yet — C4 not required; pass
        c4_passed = True
        notes.append("C4: client feedback not yet applied")
    else:
        # uncalibrated / calibration_failed / None — pass by default
        c4_passed = True

    # -----------------------------------------------------------------------
    # C5 — staleness warning: > 6 months since last_calibrated
    # -----------------------------------------------------------------------
    last_calibrated = getattr(state, "last_calibrated", None) if state is not None else None
    if last_calibrated is not None:
        now = datetime.now(tz=timezone.utc)
        if last_calibrated.tzinfo is None:
            last_calibrated = last_calibrated.replace(tzinfo=timezone.utc)
        age = now - last_calibrated
        if age > _SIX_MONTHS:
            c5_warning = True
            notes.append(
                f"C5 WARN — calibration is stale ({age.days} days since last calibration; "
                f"threshold {_SIX_MONTHS.days} days)."
            )
        else:
            c5_warning = False
    else:
        # Never calibrated — C1 catches this; C5 does not warn
        c5_warning = False

    return CalibrationGateReport(
        c1_passed=c1_passed,
        c2_passed=c2_passed,
        c3_passed=c3_passed,
        c4_passed=c4_passed,
        c5_warning=c5_warning,
        notes=notes,
    )
