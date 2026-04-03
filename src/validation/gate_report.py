"""src/validation/gate_report.py

Structured gate report objects and CLI output formatters for Sprint 21
simulation quality gates.

Provides:
  - SimulationGateReport  dataclass collecting S1-S4, BV3, and BV6 results
  - format_gate_report()  multi-line CLI string (matches regenerate_pipeline style)
  - format_gate_summary() one-line banner string for sidebar / post-run output
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.validation.simulation_gates import GateResult
    from src.validation.bv3_temporal import BV3Result
    from src.validation.bv6_override import BV6Result


# ---------------------------------------------------------------------------
# SimulationGateReport dataclass
# ---------------------------------------------------------------------------


@dataclass
class SimulationGateReport:
    """Collected results for one pipeline run's simulation quality gates.

    Attributes
    ----------
    s_gates:
        S1–S4 GateResult objects (one per gate).
    bv3_results:
        BV3Result objects, one per sample persona that was run through the
        BV3 temporal consistency arc.  Empty when --simulate was not used.
    bv6_results:
        BV6Result objects, one per sample persona that was run through the
        BV6 override scenario suite.  Empty when --simulate was not used.
    """

    s_gates: "list[GateResult]"
    bv3_results: "list[BV3Result]" = field(default_factory=list)
    bv6_results: "list[BV6Result]" = field(default_factory=list)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def all_passed(self) -> bool:
        """True if every non-warning gate passed.

        Warning gates (warning=True) count as passed for this property.
        """
        return (
            all(g.passed for g in self.s_gates)
            and all(r.passed for r in self.bv3_results)
            and all(r.passed for r in self.bv6_results)
        )

    @property
    def has_warnings(self) -> bool:
        """True if any S-gate has warning=True."""
        return any(g.warning for g in self.s_gates)

    @property
    def warning_count(self) -> int:
        """Number of S-gates with warning=True."""
        return sum(1 for g in self.s_gates if g.warning)

    @property
    def fail_count(self) -> int:
        """Number of gates (S + BV3 + BV6) that failed (passed=False)."""
        s_fails = sum(1 for g in self.s_gates if not g.passed)
        bv3_fails = sum(1 for r in self.bv3_results if not r.passed)
        bv6_fails = sum(1 for r in self.bv6_results if not r.passed)
        return s_fails + bv3_fails + bv6_fails


# ---------------------------------------------------------------------------
# Internal formatting helpers
# ---------------------------------------------------------------------------

_GATE_NAME_WIDTH = 26   # left-aligned column width for gate name


def _status_label(passed: bool, warning: bool) -> str:
    if warning:
        return "WARN"
    return "PASS" if passed else "FAIL"


def _format_s_gate_line(gate: "GateResult") -> str:
    """Format one S-gate as a fixed-width CLI line.

    Example:
      S1 Zero error rate        PASS   200/200 personas loaded
      S4 WTP plausibility       WARN   Median WTP: ₹656 (1.1% from ask)    [threshold: ±30%]
      S2 Decision diversity     FAIL   Max: 'buy' at 95.0%    [action: Review stimulus design]
    """
    # Gate name — use the `gate` field (e.g. "S1") as prefix, then readable label
    # simulation_gates.py stores a short code in `gate` and human text in `threshold`.
    # We reconstruct a display name from the gate code + the threshold string.
    gate_code = gate.gate          # "S1", "S2", "S3", "S4"
    # Build a readable short name from the threshold description
    _name_map = {
        "S1": "Zero error rate",
        "S2": "Decision diversity",
        "S3": "Driver coherence",
        "S4": "WTP plausibility",
    }
    readable = _name_map.get(gate_code, gate_code)
    display_name = f"{gate_code} {readable}"

    status = _status_label(gate.passed, gate.warning)
    actual = gate.actual or ""
    threshold_note = gate.threshold or ""

    # Truncate threshold note to bracketed form if it looks long
    # (the gate stores the full sentence; we want a short bracket notation)
    _threshold_bracket = {
        "S2": "[threshold: < 90%]",
        "S3": "[threshold: >= 70%]",
        "S4": "[threshold: ±30%]",
    }
    bracket = _threshold_bracket.get(gate_code, "")

    name_col = display_name.ljust(_GATE_NAME_WIDTH)

    if not gate.passed and gate.action_required:
        action_str = f"    [action: {gate.action_required}]"
        line = f"  {name_col}{status}   {actual}{action_str}"
    elif gate.warning and bracket:
        line = f"  {name_col}{status}   {actual}    {bracket}"
    else:
        line = f"  {name_col}{status}   {actual}"

    return line


def _format_bv3_section(bv3_results: "list[BV3Result]") -> str:
    """Format the BV3 section (one summary line)."""
    if not bv3_results:
        return "  BV3 Temporal consistency  not run (--simulate required)"

    total = len(bv3_results)
    passed_count = sum(1 for r in bv3_results if r.passed)
    overall_passed = passed_count == total

    status = "PASS" if overall_passed else "FAIL"

    # Compute average confidence delta across positive arcs
    avg_delta_parts = []
    for r in bv3_results:
        seq = r.confidence_sequence
        if len(seq) >= 2:
            avg_delta_parts.append(seq[-1] - seq[0])
    if avg_delta_parts:
        avg_delta = sum(avg_delta_parts) / len(avg_delta_parts)
        detail = (
            f"{passed_count}/{total} sample personas passed "
            f"(avg confidence +{avg_delta:.0f} across positive arc)"
        )
    else:
        detail = f"{passed_count}/{total} sample personas passed"

    name_col = "BV3 Temporal consistency".ljust(_GATE_NAME_WIDTH)
    return f"  {name_col}{status}   {detail}"


def _format_bv6_section(bv6_results: "list[BV6Result]") -> str:
    """Format the BV6 section (one summary line)."""
    if not bv6_results:
        return "  BV6 Override scenarios    not run (--simulate required)"

    total = len(bv6_results)
    passed_count = sum(1 for r in bv6_results if r.passed)
    overall_passed = passed_count == total

    status = "PASS" if overall_passed else "FAIL"

    # Average departures across all results
    avg_departures = sum(r.override_departures for r in bv6_results) / total
    detail = (
        f"{passed_count}/{total} sample personas passed "
        f"({avg_departures:.1f} avg departures)"
    )

    name_col = "BV6 Override scenarios".ljust(_GATE_NAME_WIDTH)
    return f"  {name_col}{status}   {detail}"


# ---------------------------------------------------------------------------
# Public formatters
# ---------------------------------------------------------------------------


def format_gate_report(report: SimulationGateReport) -> str:
    """Return a multi-line CLI string summarising all gate results.

    Matches the print style of regenerate_pipeline.py Stage 5 output.

    Example output::

        === Simulation Quality Gates ===

          S1 Zero error rate        PASS   200/200 personas loaded
          S2 Decision diversity     PASS   Max: 'buy' at 62.4%
          S3 Driver coherence       PASS   84.2% of driver lists contain domain keywords
          S4 WTP plausibility       WARN   Median WTP: ₹656 (1.1% from ask)    [threshold: ±30%]

          BV3 Temporal consistency  PASS   2/2 sample personas passed (avg confidence +14 across positive arc)
          BV6 Override scenarios    PASS   2/2 sample personas passed (1.5 avg departures)

          Overall: PASS  (1 warning)

    Parameters
    ----------
    report : SimulationGateReport
        The collected gate results to format.

    Returns
    -------
    str
        A ready-to-print multi-line string (no trailing newline).
    """
    lines: list[str] = []
    lines.append("=== Simulation Quality Gates ===")
    lines.append("")

    # S1–S4 gate lines
    for gate in report.s_gates:
        lines.append(_format_s_gate_line(gate))

    lines.append("")

    # BV3 and BV6 sections
    lines.append(_format_bv3_section(report.bv3_results))
    lines.append(_format_bv6_section(report.bv6_results))
    lines.append("")

    # Overall verdict
    overall_passed = report.all_passed
    overall_label = "PASS" if overall_passed else "FAIL"

    if report.warning_count > 0 and overall_passed:
        warning_str = (
            f"({report.warning_count} warning)"
            if report.warning_count == 1
            else f"({report.warning_count} warnings)"
        )
        overall_line = f"  Overall: {overall_label}  {warning_str}"
    elif not overall_passed:
        fail_str = (
            f"({report.fail_count} failure)"
            if report.fail_count == 1
            else f"({report.fail_count} failures)"
        )
        overall_line = f"  Overall: {overall_label}  {fail_str}"
    else:
        overall_line = f"  Overall: {overall_label}"

    lines.append(overall_line)

    return "\n".join(lines)


def format_gate_summary(report: SimulationGateReport) -> str:
    """Return a one-line banner summarising gate outcomes.

    Symbols: ✓ pass, ✗ fail, ⚠ warning.

    Example output::

        Gates: S1✓ S2✓ S3✓ S4⚠ | BV3: not run | BV6: not run

    Parameters
    ----------
    report : SimulationGateReport
        The collected gate results to summarise.

    Returns
    -------
    str
        A compact single-line string (no trailing newline).
    """
    parts: list[str] = []

    # S-gate symbols
    s_parts: list[str] = []
    for gate in report.s_gates:
        if gate.warning:
            symbol = "⚠"
        elif gate.passed:
            symbol = "✓"
        else:
            symbol = "✗"
        s_parts.append(f"{gate.gate}{symbol}")
    parts.append("Gates: " + " ".join(s_parts))

    # BV3
    if not report.bv3_results:
        parts.append("BV3: not run")
    else:
        all_bv3_passed = all(r.passed for r in report.bv3_results)
        bv3_symbol = "✓" if all_bv3_passed else "✗"
        parts.append(f"BV3: {bv3_symbol}")

    # BV6
    if not report.bv6_results:
        parts.append("BV6: not run")
    else:
        all_bv6_passed = all(r.passed for r in report.bv6_results)
        bv6_symbol = "✓" if all_bv6_passed else "✗"
        parts.append(f"BV6: {bv6_symbol}")

    return " | ".join(parts)
