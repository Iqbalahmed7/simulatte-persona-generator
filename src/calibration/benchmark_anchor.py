"""src/calibration/benchmark_anchor.py

Benchmark anchoring: compare simulation output distributions against known domain benchmarks.
Produces divergence scores and calibration adjustment recommendations.

Deterministic — no LLM calls.
Spec ref: Validity Protocol C2 (benchmark applied first time), C3 (conversion plausibility).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.validation.simulation_gates import GateResult


@dataclass
class BenchmarkReport:
    """Result of comparing simulation output against domain benchmarks."""

    conversion_divergence: float      # abs(simulated - benchmark) / benchmark
    wtp_divergence: float | None      # abs(simulated_median - benchmark_median) / benchmark_median
    c3_passed: bool                   # conversion within 0.5x-2x of benchmark
    c3_warning: bool                  # conversion outside ±20% (warn before hitting hard limit)
    recommendations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Conversion divergence: {self.conversion_divergence:.1%}"]
        if self.wtp_divergence is not None:
            lines.append(f"WTP divergence: {self.wtp_divergence:.1%}")
        lines.append(f"C3 gate: {'PASS' if self.c3_passed else 'FAIL'}")
        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")
        return "\n".join(lines)


def compare_to_benchmarks(
    cohort_summary,           # CohortSummary or dict with decision_style_distribution, consistency_scores
    benchmarks: dict,         # {"conversion_rate": float, "wtp_median": float, optional "wtp_mean": float}
    simulated_conversion: float | None = None,  # if None, estimated from cohort_summary
) -> BenchmarkReport:
    """Compare simulation output distributions against known domain benchmarks.

    Args:
        cohort_summary: CohortSummary instance or dict-like object with
                        ``decision_style_distribution`` and ``consistency_scores``.
        benchmarks: Dict containing at minimum ``"conversion_rate"`` (float).
                    Optionally ``"wtp_median"`` (float) and ``"wtp_mean"`` (float).
        simulated_conversion: Override for the simulated conversion rate.
                              If None, estimated from ``cohort_summary.decision_style_distribution``
                              using the share of "emotional" + "habitual" decision styles.

    Returns:
        BenchmarkReport with divergence scores, C3 gate result, and recommendations.
    """

    # ------------------------------------------------------------------
    # 1. Resolve simulated_conversion
    # ------------------------------------------------------------------
    if simulated_conversion is None:
        # Estimate from decision_style_distribution.
        # "emotional" and "habitual" styles are treated as likely converters.
        try:
            dist = (
                cohort_summary.decision_style_distribution
                if hasattr(cohort_summary, "decision_style_distribution")
                else cohort_summary["decision_style_distribution"]
            )
        except (KeyError, TypeError):
            dist = {}

        emotional = float(dist.get("emotional", 0.0))
        habitual = float(dist.get("habitual", 0.0))

        if emotional == 0.0 and habitual == 0.0:
            # Neither key present — fall back to 0.5
            simulated_conversion = 0.5
        else:
            simulated_conversion = emotional + habitual

    # ------------------------------------------------------------------
    # 2. Benchmark conversion
    # ------------------------------------------------------------------
    benchmark_conversion = float(benchmarks.get("conversion_rate", 0.5))

    # ------------------------------------------------------------------
    # 3. Conversion divergence
    # ------------------------------------------------------------------
    conversion_divergence = abs(simulated_conversion - benchmark_conversion) / benchmark_conversion

    # ------------------------------------------------------------------
    # 4. C3 gate: simulated must be between 0.5x and 2x of benchmark
    # ------------------------------------------------------------------
    ratio = simulated_conversion / benchmark_conversion
    c3_passed = 0.5 <= ratio <= 2.0

    # ------------------------------------------------------------------
    # 5. C3 warning: >20% off benchmark (even if within hard limit)
    # ------------------------------------------------------------------
    c3_warning = conversion_divergence > 0.20

    # ------------------------------------------------------------------
    # 6. WTP divergence (optional — requires wtp_median in benchmarks)
    # ------------------------------------------------------------------
    wtp_divergence: float | None = None

    if "wtp_median" in benchmarks:
        benchmark_wtp_median = float(benchmarks["wtp_median"])

        # Retrieve consistency_scores.mean as a rough WTP proxy
        try:
            cs = (
                cohort_summary.consistency_scores
                if hasattr(cohort_summary, "consistency_scores")
                else cohort_summary["consistency_scores"]
            )
        except (KeyError, TypeError):
            cs = {}

        consistency_mean = float(cs.get("mean", 74) if isinstance(cs, dict) else 74)

        simulated_wtp = benchmark_wtp_median * (consistency_mean / 74)
        wtp_divergence = abs(simulated_wtp - benchmark_wtp_median) / benchmark_wtp_median

    # ------------------------------------------------------------------
    # 7. Build recommendations
    # ------------------------------------------------------------------
    recommendations: list[str] = []

    if conversion_divergence > 0.30:
        recommendations.append(
            "Consider adjusting price_sensitivity bands — simulated conversion diverges"
            " significantly from benchmark"
        )

    if not c3_passed and simulated_conversion < benchmark_conversion:
        recommendations.append(
            "Simulated conversion below 0.5x benchmark — review stimulus design and"
            " trust tendency calibration"
        )

    if not c3_passed and simulated_conversion > benchmark_conversion:
        recommendations.append(
            "Simulated conversion above 2x benchmark — review over-optimistic persona tendencies"
        )

    if c3_warning:
        recommendations.append(
            "Conversion within acceptable range but >20% from benchmark — monitor on next run"
        )

    return BenchmarkReport(
        conversion_divergence=conversion_divergence,
        wtp_divergence=wtp_divergence,
        c3_passed=c3_passed,
        c3_warning=c3_warning,
        recommendations=recommendations,
    )


def check_c3(simulated_conversion: float, benchmark_conversion: float) -> GateResult:
    """C3 gate: simulated conversion within 0.5x–2x of benchmark.

    Args:
        simulated_conversion: Simulated buy / conversion rate (0.0–1.0).
        benchmark_conversion: Domain benchmark conversion rate (0.0–1.0).

    Returns:
        GateResult for gate C3.
    """
    ratio = simulated_conversion / benchmark_conversion
    passed = 0.5 <= ratio <= 2.0
    warning = abs(simulated_conversion - benchmark_conversion) / benchmark_conversion > 0.20

    return GateResult(
        gate="C3",
        passed=passed,
        threshold="Simulated conversion within 0.5x\u20132x of benchmark",
        actual=(
            f"Simulated: {simulated_conversion:.1%}, "
            f"Benchmark: {benchmark_conversion:.1%} "
            f"(ratio: {ratio:.2f}x)"
        ),
        action_required=(
            "Review stimulus design and tendency calibration" if not passed else None
        ),
        warning=warning,
    )
