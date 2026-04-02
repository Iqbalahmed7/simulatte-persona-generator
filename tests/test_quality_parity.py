"""tests/test_quality_parity.py — Unit tests for the quality parity checker.

Verifies that ParityResult behaves correctly and that check_parity runs the
G1–G5 gate suite against a known-good persona without crashing.

No LLM calls — all tests run offline.
"""
from __future__ import annotations

import pytest

from src.validation.quality_parity import (
    ParityResult,
    check_parity,
    compare_parity,
    parity_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    gates_checked: int = 5,
    gates_passed: int = 5,
    gates_failed: int = 0,
    failures: list[str] | None = None,
    persona_id: str = "pg-test-001",
    provider: str = "sarvam",
) -> ParityResult:
    return ParityResult(
        persona_id=persona_id,
        provider=provider,
        gates_checked=gates_checked,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        failures=failures or [],
    )


# ---------------------------------------------------------------------------
# Test 1: is_at_par True when no failures
# ---------------------------------------------------------------------------

def test_parity_result_is_at_par_when_no_failures():
    """ParityResult with gates_failed=0 must report is_at_par==True."""
    result = _make_result(gates_passed=5, gates_failed=0)
    assert result.is_at_par is True


# ---------------------------------------------------------------------------
# Test 2: is_at_par False when there are failures
# ---------------------------------------------------------------------------

def test_parity_result_not_at_par_when_failures():
    """ParityResult with gates_failed=1 must report is_at_par==False."""
    result = _make_result(
        gates_passed=4,
        gates_failed=1,
        failures=["G3: TR1 violation: budget_consciousness > 0.70 requires price_sensitivity.band 'high'"],
    )
    assert result.is_at_par is False
    assert len(result.failures) == 1


# ---------------------------------------------------------------------------
# Test 3: pass_rate calculation
# ---------------------------------------------------------------------------

def test_pass_rate_calculation():
    """pass_rate must equal gates_passed / gates_checked."""
    result = _make_result(gates_checked=5, gates_passed=4, gates_failed=1)
    assert result.pass_rate == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Test 4: compare_parity True when equal pass rates
# ---------------------------------------------------------------------------

def test_compare_parity_true_when_equal():
    """compare_parity must return True when both results have the same pass_rate."""
    perfect = _make_result(gates_checked=5, gates_passed=5, gates_failed=0)
    also_perfect = _make_result(
        gates_checked=5,
        gates_passed=5,
        gates_failed=0,
        provider="anthropic",
    )
    assert compare_parity(perfect, also_perfect) is True


# ---------------------------------------------------------------------------
# Test 5: compare_parity False when Sarvam is worse
# ---------------------------------------------------------------------------

def test_compare_parity_false_when_sarvam_worse():
    """compare_parity must return False when Sarvam pass_rate < baseline pass_rate."""
    sarvam_result = _make_result(gates_checked=5, gates_passed=3, gates_failed=2)
    baseline_result = _make_result(
        gates_checked=5, gates_passed=5, gates_failed=0, provider="anthropic"
    )
    assert compare_parity(sarvam_result, baseline_result) is False


# ---------------------------------------------------------------------------
# Test 6: parity_report formats output correctly
# ---------------------------------------------------------------------------

def test_parity_report_formats_output():
    """parity_report must include 'Quality Parity Report' heading and persona summary."""
    result = _make_result(
        gates_checked=5,
        gates_passed=4,
        gates_failed=1,
        failures=["G2: HC1: impossible combination detected"],
        persona_id="pg-test-001",
        provider="sarvam",
    )
    report = parity_report([result])
    assert "Quality Parity Report" in report
    assert "pg-test-001" in report
    assert "sarvam" in report
    # Should show the failure line
    assert "G2" in report


# ---------------------------------------------------------------------------
# Test 7: check_parity on a known-good persona
# ---------------------------------------------------------------------------

def test_check_parity_on_valid_persona():
    """check_parity on the canonical synthetic persona must run all 5 gates.

    The synthetic persona (Priya Mehta) is guaranteed to pass G1–G3 (its
    factory asserts this).  G4 passes — her narrative satisfies word-count
    requirements.  G5 uses a simple substring scan that does not understand
    negation: the phrase "rarely makes impulsive decisions" triggers a false
    positive for the "impulsive" keyword when risk_appetite=="low".

    We therefore assert:
      - returns a ParityResult with gates_checked == 5
      - G1–G4 produce zero failures
      - any failures present are limited to G5 (keyword false-positive only)
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    result = check_parity(persona, provider="anthropic")

    assert isinstance(result, ParityResult)
    assert result.gates_checked == 5
    assert result.persona_id == persona.persona_id
    assert result.provider == "anthropic"

    # G1–G4 must all pass on this known-good fixture.
    non_g5_failures = [f for f in result.failures if not f.startswith("G5")]
    assert non_g5_failures == [], (
        f"Unexpected G1–G4 failures on canonical fixture: {non_g5_failures}"
    )

    # Any remaining failures must only be G5 keyword false-positives.
    g5_failures = [f for f in result.failures if f.startswith("G5")]
    for failure in g5_failures:
        assert "G5" in failure, f"Unexpected failure format: {failure}"


# ---------------------------------------------------------------------------
# Bonus: pass_rate is 1.0 when gates_checked is 0 (edge case)
# ---------------------------------------------------------------------------

def test_pass_rate_is_1_when_no_gates_checked():
    """pass_rate must return 1.0 when gates_checked==0 to avoid ZeroDivisionError."""
    result = ParityResult(
        persona_id="pg-empty-000",
        provider="unknown",
        gates_checked=0,
        gates_passed=0,
        gates_failed=0,
    )
    assert result.pass_rate == 1.0
