"""tests/test_bv6.py — BV6 Override Scenario test suite.

Sprint 21 — Antigravity
No real LLM calls. run_loop is fully mocked via side_effect lists.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import asyncio
from src.validation.bv6_override import BV6Result, run_bv6, run_bv6_sync, _determine_tendency, _is_tendency_consistent, _is_override_departure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persona(
    persona_id: str = "pg-bv6-test",
    risk_appetite: str = "low",
    decision_style: str = "analytical",
):
    """Build a minimal MagicMock persona with required BV6 attributes."""
    persona = MagicMock()
    persona.persona_id = persona_id
    persona.derived_insights.risk_appetite = risk_appetite
    persona.derived_insights.decision_style = decision_style
    return persona


def _make_loop_result(decision: str = "buy", reasoning_trace: str = ""):
    """Return a (updated_persona, loop_result) pair with the given decision."""
    mock_decision = MagicMock()
    mock_decision.decision = decision
    mock_decision.reasoning_trace = reasoning_trace

    mock_result = MagicMock()
    mock_result.decision = mock_decision

    updated_persona = _make_persona()
    return updated_persona, mock_result


def _build_10_effects(
    normal_decisions: list[str],
    override_decisions: list[str],
    override_reasoning: list[str] | None = None,
):
    """Build 10 side_effect entries: 8 normal + 2 override."""
    assert len(normal_decisions) == 8, "Exactly 8 normal decisions required"
    assert len(override_decisions) == 2, "Exactly 2 override decisions required"

    if override_reasoning is None:
        override_reasoning = ["", ""]

    effects = []

    for d in normal_decisions:
        effects.append(_make_loop_result(decision=d, reasoning_trace="short"))

    for d, trace in zip(override_decisions, override_reasoning):
        effects.append(_make_loop_result(decision=d, reasoning_trace=trace))

    return effects


PATCH_TARGET = "src.cognition.loop.run_loop"


# ---------------------------------------------------------------------------
# Unit tests for _determine_tendency
# ---------------------------------------------------------------------------

class TestDetermineTendency:
    def test_low_risk_appetite_returns_avoid_risk(self):
        persona = _make_persona(risk_appetite="low")
        assert _determine_tendency(persona) == "avoid risk / prefer familiar"

    def test_habitual_style_returns_stick_with_known(self):
        persona = _make_persona(risk_appetite="medium", decision_style="habitual")
        assert _determine_tendency(persona) == "stick with known brand"

    def test_other_style_returns_analytical(self):
        persona = _make_persona(risk_appetite="medium", decision_style="analytical")
        assert _determine_tendency(persona) == "analytical / research-first"


# ---------------------------------------------------------------------------
# Unit tests for _is_tendency_consistent
# ---------------------------------------------------------------------------

class TestIsTendencyConsistent:
    def test_avoid_risk_buy_is_consistent(self):
        assert _is_tendency_consistent("buy", "avoid risk / prefer familiar") is True

    def test_avoid_risk_reject_is_inconsistent(self):
        assert _is_tendency_consistent("reject", "avoid risk / prefer familiar") is False

    def test_avoid_risk_switch_is_inconsistent(self):
        assert _is_tendency_consistent("switch", "avoid risk / prefer familiar") is False

    def test_habitual_buy_is_consistent(self):
        assert _is_tendency_consistent("buy", "stick with known brand") is True

    def test_habitual_reject_is_inconsistent(self):
        assert _is_tendency_consistent("reject", "stick with known brand") is False

    def test_analytical_any_is_consistent(self):
        assert _is_tendency_consistent("reject", "analytical / research-first") is True
        assert _is_tendency_consistent("buy", "analytical / research-first") is True


# ---------------------------------------------------------------------------
# Unit tests for _is_override_departure
# ---------------------------------------------------------------------------

class TestIsOverrideDeparture:
    def test_override1_buy_with_cost_mention_and_long_trace(self):
        long_trace = "Despite the high price of ₹799, I will buy because the paediatrician says malnutrition is a serious risk for my child and I cannot afford to ignore this."
        assert _is_override_departure(0, "buy", long_trace, "avoid risk / prefer familiar") is True

    def test_override1_buy_with_short_trace_fails(self):
        short_trace = "buy due to cost"
        assert _is_override_departure(0, "buy", short_trace, "avoid risk / prefer familiar") is False

    def test_override2_not_buy_with_long_trace(self):
        long_trace = "After reviewing the blood tests and seeing no improvement in iron or calcium levels over six months, I am choosing to research alternatives and not continue buying this supplement."
        assert _is_override_departure(1, "defer", long_trace, "avoid risk / prefer familiar") is True

    def test_override2_buy_is_not_departure(self):
        long_trace = "Even though the tests show no improvement, I will continue buying because the paediatrician suggested patience."
        assert _is_override_departure(1, "buy", long_trace, "avoid risk / prefer familiar") is False


# ---------------------------------------------------------------------------
# Integration tests via run_bv6_sync (mocked run_loop)
# ---------------------------------------------------------------------------

class TestRunBV6Integration:

    def _run(self, effects, persona=None):
        if persona is None:
            persona = _make_persona()
        with patch(PATCH_TARGET, new_callable=AsyncMock) as mock_rl:
            mock_rl.side_effect = effects
            result = asyncio.run(run_bv6(persona))
        return result

    def test_80pct_consistent_passes_check_a(self):
        # 6 consistent "buy", 2 inconsistent "reject" → 75% → passes 70–90% band
        normal = ["buy"] * 6 + ["reject"] * 2
        long_trace = "Despite the elevated cost of ₹799/month I will buy Nutrimix because the paediatrician says malnutrition is a serious risk for my child."
        override_traces = [long_trace, ""]
        effects = _build_10_effects(normal, ["buy", "defer"], override_reasoning=override_traces)
        result = self._run(effects)
        assert result.check_a_passed is True
        assert pytest.approx(result.consistency_rate, abs=0.01) == 0.75

    def test_100pct_consistent_fails_check_a(self):
        # All 8 normal → "buy" (consistent with low risk) → 100% → fails ceiling check
        normal = ["buy"] * 8
        long_trace = "Despite high cost ₹799 the paediatrician prescribed it for malnutrition risk."
        effects = _build_10_effects(normal, ["buy", "buy"], override_reasoning=[long_trace, long_trace])
        result = self._run(effects)
        assert result.check_a_passed is False
        assert any("rigid" in r.lower() for r in result.failure_reasons)

    def test_60pct_consistent_fails_check_a(self):
        # Only 4/8 consistent (50%) → fails floor check
        normal = ["buy"] * 4 + ["reject"] * 4
        effects = _build_10_effects(normal, ["buy", "defer"])
        result = self._run(effects)
        assert result.check_a_passed is False

    def test_override_departure_with_reasoning_passes_check_b(self):
        # 6 consistent + 2 inconsistent; override 1: buy with long cost reasoning
        normal = ["buy"] * 6 + ["reject"] * 2
        long_trace = "Despite the high price of ₹799, I will buy because the paediatrician said malnutrition is a serious risk and my child needs daily supplements."
        effects = _build_10_effects(
            normal,
            ["buy", "defer"],
            override_reasoning=[long_trace, "short"],
        )
        result = self._run(effects)
        assert result.check_b_passed is True
        assert result.override_departures >= 1

    def test_no_override_departure_fails_check_b(self):
        # Both overrides have short traces → no qualifying departure
        normal = ["buy"] * 6 + ["reject"] * 2
        effects = _build_10_effects(
            normal,
            ["defer", "defer"],
            override_reasoning=["too short", "also short"],
        )
        result = self._run(effects)
        assert result.check_b_passed is False

    def test_not_100pct_passes_check_c(self):
        # 7/8 normal consistent, 1 inconsistent → not 100%
        normal = ["buy"] * 7 + ["reject"] * 1
        long_trace = "Despite the high ₹799 cost I will buy because my paediatrician prescribed it for severe malnutrition risk in my child."
        effects = _build_10_effects(normal, ["buy", "defer"], override_reasoning=[long_trace, ""])
        result = self._run(effects)
        assert result.check_c_passed is True

    def test_overall_pass_all_checks(self):
        # 75% consistent (6/8) + 1 override departure → should pass all three
        normal = ["buy"] * 6 + ["reject"] * 2
        long_trace = "Despite the high price of ₹799, I will buy Nutrimix because the paediatrician warned about serious malnutrition risk for my child."
        effects = _build_10_effects(
            normal,
            ["buy", "defer"],
            override_reasoning=[long_trace, "short"],
        )
        result = self._run(effects)
        assert result.passed is True

    def test_overall_fail_too_rigid(self):
        # 100% consistent → check_a fails → overall fails
        normal = ["buy"] * 8
        long_trace = "Due to paediatrician warning about malnutrition risk and high cost I will buy."
        effects = _build_10_effects(
            normal,
            ["buy", "buy"],
            override_reasoning=[long_trace, long_trace],
        )
        result = self._run(effects)
        assert result.passed is False

    def test_persona_id_recorded(self):
        persona = _make_persona(persona_id="pg-bv6-test")
        normal = ["buy"] * 6 + ["reject"] * 2
        long_trace = "Despite the ₹799 cost I will buy because the paediatrician warned about malnutrition risk for my child and the health risk outweighs the price concern."
        effects = _build_10_effects(normal, ["buy", "defer"], override_reasoning=[long_trace, ""])
        with patch(PATCH_TARGET, new_callable=AsyncMock) as mock_rl:
            mock_rl.side_effect = effects
            result = asyncio.run(run_bv6(persona))
        assert result.persona_id == "pg-bv6-test"

    def test_summary_returns_string(self):
        normal = ["buy"] * 6 + ["reject"] * 2
        long_trace = "Despite the ₹799 cost the paediatrician prescribed it due to serious malnutrition risk for my child."
        effects = _build_10_effects(normal, ["buy", "defer"], override_reasoning=[long_trace, ""])
        result = self._run(effects)
        summary = result.summary()
        assert isinstance(summary, str)
        assert "BV6" in summary
