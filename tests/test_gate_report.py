"""tests/test_gate_report.py — Gate report formatter tests.

Sprint 21 — Antigravity
Builds GateResult and SimulationGateReport fixtures directly; no mocking needed.
"""
from __future__ import annotations

import pytest

from src.validation.simulation_gates import GateResult
from src.validation.gate_report import SimulationGateReport, format_gate_report, format_gate_summary


# ---------------------------------------------------------------------------
# Fixture factories
# ---------------------------------------------------------------------------

def _passing_gate(gate: str = "S1") -> GateResult:
    return GateResult(
        gate=gate,
        passed=True,
        threshold="All 5 sample personas must complete without error",
        actual="5 personas loaded successfully",
        action_required=None,
        warning=False,
    )


def _warning_gate(gate: str = "S4") -> GateResult:
    return GateResult(
        gate=gate,
        passed=True,
        threshold="Median WTP within ±30% of ask price (₹649)",
        actual="Median WTP: ₹810 (24.8% from ask)",
        action_required="Check tendency-attribute proxy formulas; may need recalibration",
        warning=True,
    )


def _failing_gate(gate: str = "S2") -> GateResult:
    return GateResult(
        gate=gate,
        passed=False,
        threshold="No single option > 90%",
        actual="Max: 'buy' at 95.0%",
        action_required="Review stimulus design; may indicate broken persona or prompt issue",
        warning=False,
    )


def _all_passing_report() -> SimulationGateReport:
    return SimulationGateReport(
        s_gates=[
            _passing_gate("S1"),
            _passing_gate("S2"),
            _passing_gate("S3"),
            _passing_gate("S4"),
        ],
        bv3_results=[],
        bv6_results=[],
    )


def _report_with_failing_gate() -> SimulationGateReport:
    return SimulationGateReport(
        s_gates=[
            _passing_gate("S1"),
            _failing_gate("S2"),
            _passing_gate("S3"),
            _passing_gate("S4"),
        ],
        bv3_results=[],
        bv6_results=[],
    )


def _report_with_warning_gate() -> SimulationGateReport:
    return SimulationGateReport(
        s_gates=[
            _passing_gate("S1"),
            _passing_gate("S2"),
            _passing_gate("S3"),
            _warning_gate("S4"),
        ],
        bv3_results=[],
        bv6_results=[],
    )


# Minimal BV3 and BV6 result stubs
def _bv3_result(passed: bool = True):
    from unittest.mock import MagicMock
    r = MagicMock()
    r.passed = passed
    r.confidence_sequence = [55, 62, 68, 74, 79] if passed else [70, 60, 50, 40, 30]
    r.override_departures = 1 if passed else 0
    return r


def _bv6_result(passed: bool = True):
    from unittest.mock import MagicMock
    r = MagicMock()
    r.passed = passed
    r.override_departures = 1 if passed else 0
    return r


# ---------------------------------------------------------------------------
# format_gate_report tests
# ---------------------------------------------------------------------------

class TestFormatGateReport:
    def test_format_shows_pass_for_passing_gate(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        assert "PASS" in output

    def test_format_shows_fail_for_failing_gate(self):
        report = _report_with_failing_gate()
        output = format_gate_report(report)
        assert "FAIL" in output

    def test_format_shows_warn_for_warning_gate(self):
        report = _report_with_warning_gate()
        output = format_gate_report(report)
        assert "WARN" in output

    def test_format_bv3_not_run_when_empty(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        assert "not run" in output.lower()

    def test_format_overall_pass_all_gates_pass(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        assert "Overall: PASS" in output

    def test_format_overall_fail_any_gate_fails(self):
        report = _report_with_failing_gate()
        output = format_gate_report(report)
        assert "Overall: FAIL" in output

    def test_format_includes_all_four_gate_codes(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        for code in ["S1", "S2", "S3", "S4"]:
            assert code in output

    def test_format_returns_string(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        assert isinstance(output, str)

    def test_format_includes_gate_header(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        assert "Simulation Quality Gates" in output

    def test_format_shows_warning_count_when_warn(self):
        report = _report_with_warning_gate()
        output = format_gate_report(report)
        assert "warning" in output.lower()

    def test_format_bv3_present_when_results_provided(self):
        report = SimulationGateReport(
            s_gates=[_passing_gate("S1"), _passing_gate("S2"), _passing_gate("S3"), _passing_gate("S4")],
            bv3_results=[_bv3_result(passed=True)],
            bv6_results=[],
        )
        output = format_gate_report(report)
        assert "not run" not in output.split("BV3")[1].split("\n")[0]

    def test_format_bv6_not_run_when_empty(self):
        report = _all_passing_report()
        output = format_gate_report(report)
        assert "BV6" in output
        # The BV6 line should say "not run"
        bv6_line = [line for line in output.split("\n") if "BV6" in line][0]
        assert "not run" in bv6_line


# ---------------------------------------------------------------------------
# format_gate_summary tests
# ---------------------------------------------------------------------------

class TestFormatGateSummary:
    def test_summary_uses_checkmarks_for_passing(self):
        report = _all_passing_report()
        summary = format_gate_summary(report)
        assert "✓" in summary

    def test_summary_uses_cross_for_fail(self):
        report = _report_with_failing_gate()
        summary = format_gate_summary(report)
        assert "✗" in summary

    def test_summary_uses_warning_symbol(self):
        report = _report_with_warning_gate()
        summary = format_gate_summary(report)
        assert "⚠" in summary

    def test_summary_bv3_not_run_when_empty(self):
        report = _all_passing_report()
        summary = format_gate_summary(report)
        assert "BV3: not run" in summary

    def test_summary_bv6_not_run_when_empty(self):
        report = _all_passing_report()
        summary = format_gate_summary(report)
        assert "BV6: not run" in summary

    def test_summary_includes_all_gate_codes(self):
        report = _all_passing_report()
        summary = format_gate_summary(report)
        for code in ["S1", "S2", "S3", "S4"]:
            assert code in summary

    def test_summary_returns_single_line(self):
        report = _all_passing_report()
        summary = format_gate_summary(report)
        assert "\n" not in summary

    def test_summary_bv3_checkmark_when_passed(self):
        report = SimulationGateReport(
            s_gates=[_passing_gate("S1"), _passing_gate("S2"), _passing_gate("S3"), _passing_gate("S4")],
            bv3_results=[_bv3_result(passed=True)],
            bv6_results=[],
        )
        summary = format_gate_summary(report)
        assert "BV3: ✓" in summary

    def test_summary_bv3_cross_when_failed(self):
        report = SimulationGateReport(
            s_gates=[_passing_gate("S1"), _passing_gate("S2"), _passing_gate("S3"), _passing_gate("S4")],
            bv3_results=[_bv3_result(passed=False)],
            bv6_results=[],
        )
        summary = format_gate_summary(report)
        assert "BV3: ✗" in summary


# ---------------------------------------------------------------------------
# SimulationGateReport property tests
# ---------------------------------------------------------------------------

class TestSimulationGateReportProperties:
    def test_all_passed_property(self):
        report = _all_passing_report()
        assert report.all_passed is True

    def test_all_passed_false_when_gate_fails(self):
        report = _report_with_failing_gate()
        assert report.all_passed is False

    def test_has_warnings_property(self):
        report = _report_with_warning_gate()
        assert report.has_warnings is True

    def test_has_warnings_false_when_no_warnings(self):
        report = _all_passing_report()
        assert report.has_warnings is False

    def test_warning_count(self):
        report = _report_with_warning_gate()
        assert report.warning_count == 1

    def test_warning_count_zero_when_no_warnings(self):
        report = _all_passing_report()
        assert report.warning_count == 0

    def test_fail_count_zero_when_all_pass(self):
        report = _all_passing_report()
        assert report.fail_count == 0

    def test_fail_count_counts_failed_gates(self):
        report = _report_with_failing_gate()
        assert report.fail_count == 1

    def test_all_passed_includes_bv3(self):
        report = SimulationGateReport(
            s_gates=[_passing_gate("S1"), _passing_gate("S2"), _passing_gate("S3"), _passing_gate("S4")],
            bv3_results=[_bv3_result(passed=False)],
            bv6_results=[],
        )
        assert report.all_passed is False

    def test_all_passed_true_no_bv_results(self):
        # With no BV results, all_passed depends only on s_gates
        report = _all_passing_report()
        assert report.all_passed is True
