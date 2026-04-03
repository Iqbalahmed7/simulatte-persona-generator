"""tests/test_simulation_gates_s1s4.py — S1–S4 simulation quality gate tests.

Sprint 21 — Antigravity
All deterministic; no mocking of production logic needed.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.validation.simulation_gates import (
    GateResult,
    check_s1,
    check_s2,
    check_s3,
    check_s4,
    run_all_gates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persona(simulation_state="completed", persona_id: str = "pg-test"):
    """Build a minimal MagicMock persona for S1."""
    p = MagicMock()
    p.persona_id = persona_id
    p.memory.working.simulation_state = simulation_state
    return p


# ---------------------------------------------------------------------------
# S1 — Zero error rate
# ---------------------------------------------------------------------------

class TestS1:
    def test_s1_passes_with_valid_personas(self):
        personas = [_make_persona() for _ in range(5)]
        result = check_s1(personas, sample_size=5)
        assert result.passed is True
        assert result.gate == "S1"
        assert result.warning is False

    def test_s1_fails_with_too_few_personas(self):
        personas = [_make_persona() for _ in range(3)]
        result = check_s1(personas, sample_size=5)
        assert result.passed is False

    def test_s1_fails_when_persona_has_none_state(self):
        personas = [_make_persona() for _ in range(4)]
        personas.append(_make_persona(simulation_state=None))
        result = check_s1(personas, sample_size=5)
        assert result.passed is False

    def test_s1_fails_when_persona_has_error_marker(self):
        personas = [_make_persona() for _ in range(4)]
        personas.append(_make_persona(simulation_state="error"))
        result = check_s1(personas, sample_size=5)
        assert result.passed is False

    def test_s1_action_required_on_failure(self):
        result = check_s1([], sample_size=5)
        assert result.action_required is not None
        assert "pipeline" in result.action_required.lower()

    def test_s1_no_action_on_success(self):
        personas = [_make_persona() for _ in range(5)]
        result = check_s1(personas, sample_size=5)
        assert result.action_required is None


# ---------------------------------------------------------------------------
# S2 — Decision diversity
# ---------------------------------------------------------------------------

class TestS2:
    def test_s2_passes_below_threshold(self):
        # 60% buy — well below 80% warn threshold
        decisions = ["buy"] * 6 + ["defer"] * 4
        result = check_s2(decisions)
        assert result.passed is True
        assert result.warning is False
        assert result.gate == "S2"

    def test_s2_warns_near_threshold(self):
        # 85% buy — between 80% and 90%: warn but pass
        decisions = ["buy"] * 85 + ["defer"] * 15
        result = check_s2(decisions)
        assert result.passed is True
        assert result.warning is True

    def test_s2_fails_above_threshold(self):
        # 95% buy — exceeds 90% hard ceiling
        decisions = ["buy"] * 95 + ["defer"] * 5
        result = check_s2(decisions)
        assert result.passed is False
        assert result.warning is False

    def test_s2_empty_decisions_passes_with_warning(self):
        result = check_s2([])
        assert result.passed is True
        assert result.warning is True

    def test_s2_action_required_on_fail(self):
        decisions = ["buy"] * 95 + ["defer"] * 5
        result = check_s2(decisions)
        assert result.action_required is not None

    def test_s2_diverse_decisions_pass(self):
        decisions = ["buy", "defer", "reject", "research_more"] * 10
        result = check_s2(decisions)
        assert result.passed is True
        assert result.warning is False


# ---------------------------------------------------------------------------
# S3 — Driver coherence
# ---------------------------------------------------------------------------

class TestS3:
    def test_s3_passes_with_keywords(self):
        # Each driver list contains "pediatrician" — 100% relevance (well above 70%)
        drivers = [["pediatrician recommended it for daily nutrition"]] * 10
        result = check_s3(drivers, domain_keywords=["pediatrician", "price"])
        assert result.passed is True
        assert result.gate == "S3"

    def test_s3_fails_without_keywords(self):
        drivers = [["something completely irrelevant"]] * 10
        result = check_s3(drivers, domain_keywords=["pediatrician"])
        assert result.passed is False

    def test_s3_autopasses_empty_keywords(self):
        drivers = [["any content"]] * 5
        result = check_s3(drivers, domain_keywords=[])
        assert result.passed is True
        assert result.warning is True

    def test_s3_autopasses_empty_drivers(self):
        result = check_s3([], domain_keywords=["pediatrician"])
        assert result.passed is True
        assert result.warning is True

    def test_s3_partial_match_below_70pct_fails(self):
        # 2 out of 10 have keyword → 20% relevance < 70%
        drivers = [["pediatrician recommended"]] * 2 + [["irrelevant text"]] * 8
        result = check_s3(drivers, domain_keywords=["pediatrician"])
        assert result.passed is False

    def test_s3_exact_70pct_passes(self):
        # 7 out of 10 contain keyword → exactly 70%
        drivers = [["pediatrician recommended"]] * 7 + [["irrelevant"]] * 3
        result = check_s3(drivers, domain_keywords=["pediatrician"])
        assert result.passed is True

    def test_s3_case_insensitive_match(self):
        drivers = [["Pediatrician recommended Nutrimix"]] * 10
        result = check_s3(drivers, domain_keywords=["pediatrician"])
        assert result.passed is True


# ---------------------------------------------------------------------------
# S4 — WTP plausibility
# ---------------------------------------------------------------------------

class TestS4:
    def test_s4_passes_within_range(self):
        # Median ~648, ask 649 → deviation < 1% → well within 20% tight band
        wtp = [640, 650, 655, 645]
        result = check_s4(wtp, ask_price=649)
        assert result.passed is True
        assert result.warning is False
        assert result.gate == "S4"

    def test_s4_warns_near_boundary(self):
        # Median ~810, ask 649 → deviation ~24.8% → warn zone (20–30%)
        wtp = [800, 810, 820]
        result = check_s4(wtp, ask_price=649)
        assert result.passed is True
        assert result.warning is True

    def test_s4_fails_outside_range(self):
        # Median ~1250, ask 649 → deviation ~92% → far exceeds 30%
        wtp = [1200, 1300, 1250]
        result = check_s4(wtp, ask_price=649)
        assert result.passed is False
        assert result.warning is False

    def test_s4_no_data_autopasses(self):
        result = check_s4([], ask_price=649)
        assert result.passed is True
        assert result.warning is True

    def test_s4_zeros_filtered_out(self):
        # Zeros should be ignored; remaining values [640, 650] → median 645 near ask
        wtp = [0, 640, 650, 0]
        result = check_s4(wtp, ask_price=649)
        assert result.passed is True

    def test_s4_action_required_on_fail(self):
        wtp = [1200, 1300, 1250]
        result = check_s4(wtp, ask_price=649)
        assert result.action_required is not None

    def test_s4_actual_str_includes_median(self):
        wtp = [640, 650, 655, 645]
        result = check_s4(wtp, ask_price=649)
        assert "Median WTP" in result.actual


# ---------------------------------------------------------------------------
# run_all_gates
# ---------------------------------------------------------------------------

class TestRunAllGates:
    def test_run_all_gates_returns_four(self):
        personas = [_make_persona() for _ in range(5)]
        decisions = ["buy"] * 6 + ["defer"] * 4
        drivers = [["pediatrician recommended"]] * 10
        wtp = [640, 650, 655, 645, 648]
        results = run_all_gates(
            personas=personas,
            decisions=decisions,
            key_drivers=drivers,
            wtp_values=wtp,
            ask_price=649,
            domain_keywords=["pediatrician"],
        )
        assert len(results) == 4

    def test_run_all_gates_returns_correct_gate_codes(self):
        personas = [_make_persona() for _ in range(5)]
        results = run_all_gates(
            personas=personas,
            decisions=["buy"] * 6 + ["defer"] * 4,
            key_drivers=[["pediatrician recommended"]] * 10,
            wtp_values=[640, 650, 655],
            ask_price=649,
            domain_keywords=["pediatrician"],
        )
        gate_codes = [r.gate for r in results]
        assert gate_codes == ["S1", "S2", "S3", "S4"]

    def test_run_all_gates_default_no_keywords(self):
        """domain_keywords defaults to [] when not provided."""
        personas = [_make_persona() for _ in range(5)]
        results = run_all_gates(
            personas=personas,
            decisions=["buy"] * 5 + ["defer"] * 5,
            key_drivers=[["any driver"]] * 5,
            wtp_values=[640, 650],
            ask_price=649,
        )
        assert len(results) == 4
        # S3 with no keywords autopasses with warning
        s3 = results[2]
        assert s3.passed is True
        assert s3.warning is True
