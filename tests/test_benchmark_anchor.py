"""tests/test_benchmark_anchor.py — Sprint 22 benchmark anchor tests.

Antigravity — Sprint 22
Tests compare_to_benchmarks() and check_c3() from benchmark_anchor.py.
No LLM calls. Deterministic only.
"""
from __future__ import annotations

import pytest

from src.calibration.benchmark_anchor import (
    BenchmarkReport,
    compare_to_benchmarks,
    check_c3 as benchmark_check_c3,
)
from src.validation.simulation_gates import GateResult


# ---------------------------------------------------------------------------
# Helpers / minimal cohort_summary duck-types
# ---------------------------------------------------------------------------

class _FakeCohortSummary:
    """Minimal duck-typed cohort summary for compare_to_benchmarks."""

    def __init__(
        self,
        decision_style_distribution: dict | None = None,
        consistency_scores: dict | None = None,
    ):
        self.decision_style_distribution = decision_style_distribution or {}
        self.consistency_scores = consistency_scores or {"mean": 74}


# ---------------------------------------------------------------------------
# compare_to_benchmarks — conversion divergence
# ---------------------------------------------------------------------------

class TestCompareToBenchmarks:

    def test_exact_match_gives_zero_divergence(self):
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.40
        )
        assert report.conversion_divergence == pytest.approx(0.0)

    def test_exact_match_c3_passed(self):
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.40
        )
        assert report.c3_passed is True

    def test_exact_match_no_c3_warning(self):
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.40
        )
        assert report.c3_warning is False

    def test_2x_benchmark_c3_passed_boundary(self):
        """Simulated = 2x benchmark → ratio exactly 2.0 → should PASS."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.30}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.60
        )
        assert report.c3_passed is True

    def test_2_1x_benchmark_c3_fails(self):
        """Simulated = 2.1x benchmark → ratio 2.1 → should FAIL."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.30}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.63
        )
        assert report.c3_passed is False

    def test_0_5x_benchmark_c3_passed_boundary(self):
        """Simulated = 0.5x benchmark → ratio exactly 0.5 → should PASS."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.20
        )
        assert report.c3_passed is True

    def test_0_49x_benchmark_c3_fails(self):
        """Simulated = 0.49x benchmark → ratio 0.49 → should FAIL."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        # 0.49 * 0.40 = 0.196
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.196
        )
        assert report.c3_passed is False

    def test_c3_warning_when_divergence_exceeds_20_pct(self):
        """Divergence of 25% → c3_warning True."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        # abs(0.50 - 0.40)/0.40 = 25%
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.50
        )
        assert report.c3_warning is True

    def test_no_c3_warning_when_divergence_within_20_pct(self):
        """Divergence of 10% → c3_warning False."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.40}
        # abs(0.44 - 0.40)/0.40 = 10%
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.44
        )
        assert report.c3_warning is False

    def test_wtp_divergence_is_none_when_no_wtp_median_in_benchmarks(self):
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.30}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.30
        )
        assert report.wtp_divergence is None

    def test_wtp_divergence_computed_when_wtp_median_in_benchmarks(self):
        summary = _FakeCohortSummary(consistency_scores={"mean": 74})
        benchmarks = {"conversion_rate": 0.30, "wtp_median": 500.0}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.30
        )
        # consistency_mean==74 → simulated_wtp = 500 * (74/74) = 500 → divergence=0
        assert report.wtp_divergence is not None
        assert report.wtp_divergence == pytest.approx(0.0)

    def test_recommendations_populated_when_divergence_above_30_pct(self):
        """Conversion divergence > 30% → at least one recommendation."""
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.30}
        # abs(0.69 - 0.30)/0.30 = 130% divergence
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.69
        )
        assert len(report.recommendations) > 0

    def test_recommendations_include_price_sensitivity_hint_on_large_divergence(self):
        summary = _FakeCohortSummary()
        benchmarks = {"conversion_rate": 0.30}
        report = compare_to_benchmarks(
            summary, benchmarks, simulated_conversion=0.69
        )
        combined = " ".join(report.recommendations).lower()
        assert "price_sensitivity" in combined

    def test_simulated_conversion_none_uses_emotional_plus_habitual(self):
        """When simulated_conversion=None, estimate from decision_style_distribution."""
        summary = _FakeCohortSummary(
            decision_style_distribution={"emotional": 0.25, "habitual": 0.15, "analytical": 0.60}
        )
        benchmarks = {"conversion_rate": 0.40}
        # Estimated = 0.25 + 0.15 = 0.40 → exact match
        report = compare_to_benchmarks(summary, benchmarks, simulated_conversion=None)
        assert report.conversion_divergence == pytest.approx(0.0)
        assert report.c3_passed is True

    def test_simulated_conversion_none_fallback_to_0_5_when_both_zero(self):
        """If emotional==habitual==0, falls back to 0.5."""
        summary = _FakeCohortSummary(
            decision_style_distribution={"analytical": 1.0}
        )
        benchmarks = {"conversion_rate": 0.50}
        report = compare_to_benchmarks(summary, benchmarks, simulated_conversion=None)
        assert report.conversion_divergence == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# check_c3 from benchmark_anchor (returns GateResult)
# ---------------------------------------------------------------------------

class TestBenchmarkCheckC3:

    def test_ratio_within_range_returns_passed_true(self):
        result = benchmark_check_c3(0.30, 0.30)
        assert isinstance(result, GateResult)
        assert result.passed is True

    def test_ratio_at_2x_passes(self):
        result = benchmark_check_c3(0.60, 0.30)
        assert result.passed is True

    def test_ratio_above_2x_fails(self):
        result = benchmark_check_c3(0.63, 0.30)
        assert result.passed is False

    def test_ratio_at_0_5x_passes(self):
        result = benchmark_check_c3(0.15, 0.30)
        assert result.passed is True

    def test_ratio_below_0_5x_fails(self):
        result = benchmark_check_c3(0.10, 0.30)
        assert result.passed is False

    def test_gate_label_is_c3(self):
        result = benchmark_check_c3(0.30, 0.30)
        assert result.gate == "C3"

    def test_action_required_is_none_when_passed(self):
        result = benchmark_check_c3(0.30, 0.30)
        assert result.action_required is None

    def test_action_required_set_when_failed(self):
        result = benchmark_check_c3(0.10, 0.30)
        assert result.action_required is not None

    def test_actual_field_contains_ratio(self):
        result = benchmark_check_c3(0.30, 0.30)
        assert "ratio" in result.actual.lower() or "1.00" in result.actual

    def test_warning_false_when_within_20_pct(self):
        result = benchmark_check_c3(0.32, 0.30)
        assert result.warning is False

    def test_warning_true_when_outside_20_pct_but_within_2x(self):
        result = benchmark_check_c3(0.40, 0.30)
        # abs(0.40-0.30)/0.30 = 33.3% > 20%
        assert result.warning is True
