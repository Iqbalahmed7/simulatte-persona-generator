"""tests/test_bv3.py — BV3 Temporal Consistency test suite.

Sprint 21 — Antigravity
No real LLM calls. run_loop is fully mocked via side_effect lists.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.validation.bv3_temporal import BV3Result, run_bv3_sync, _check_a, _check_b, _check_c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persona(persona_id: str = "pg-bv3-test", reflections=None):
    """Build a minimal MagicMock persona with the required shape."""
    if reflections is None:
        reflections = []
    persona = MagicMock()
    persona.persona_id = persona_id
    persona.memory.working.reflections = reflections
    return persona


def _make_reflection(content: str):
    r = MagicMock()
    r.content = content
    return r


def _make_loop_result(confidence: int | None = None, reasoning_trace: str = ""):
    """Return a (persona, loop_result) pair as run_loop would."""
    mock_decision = MagicMock()
    mock_decision.confidence = confidence
    mock_decision.reasoning_trace = reasoning_trace

    mock_result = MagicMock()
    if confidence is None:
        mock_result.decision = None
    else:
        mock_result.decision = mock_decision

    return mock_result


def _build_side_effects(
    pos_confidences: list[int | None],
    reflections_after_pos: list,
    mixed_confidences: list[int | None],
    final_reasoning: str,
):
    """
    Build the side_effect list for run_loop (10 calls total):
      - 5 positive stimuli  → pos_confidences
      - 5 mixed stimuli     → mixed_confidences (last one has decision with final_reasoning)

    Each side_effect entry is (updated_persona, loop_result).
    updated_persona always has the given reflections set (they are read after stimulus 5).
    """
    effects = []
    updated_persona = _make_persona(reflections=reflections_after_pos)

    # Positive stimuli (5 calls)
    for conf in pos_confidences:
        loop_result = _make_loop_result(confidence=conf)
        effects.append((updated_persona, loop_result))

    # Mixed stimuli (5 calls) — last one carries the final decision reasoning
    for i, conf in enumerate(mixed_confidences):
        is_final = i == len(mixed_confidences) - 1
        reasoning = final_reasoning if is_final else ""
        loop_result = _make_loop_result(confidence=conf if is_final else None, reasoning_trace=reasoning)
        if not is_final:
            loop_result.decision = None
        effects.append((updated_persona, loop_result))

    return effects, updated_persona


# ---------------------------------------------------------------------------
# Unit tests for _check_a (confidence trend)
# ---------------------------------------------------------------------------

class TestCheckA:
    def test_monotonic_confidence_passes_check_a(self):
        passed, reasons = _check_a([55, 62, 68, 74, 79])
        assert passed is True
        assert reasons == []

    def test_flat_confidence_fails_check_a(self):
        # last (60) >= first (60), but let's ensure not-improving also caught:
        # Actually [60,58,61,59,60]: last==first but has dips <= 15, so passes?
        # The spec says: last >= first AND no more than 1 downward step > 15 pts.
        # [60,58,61,59,60]: last(60) >= first(60), dips > 15 = 0. Would PASS per spec.
        # Use values where last < first to force fail:
        passed, reasons = _check_a([60, 59, 58, 57, 55])
        assert passed is False
        assert len(reasons) > 0

    def test_large_dip_fails_check_a(self):
        # Two dips > 15 points → fail
        passed, reasons = _check_a([70, 50, 70, 50, 70])
        # dip 70→50 = 20 pts, occurs twice
        assert passed is False

    def test_single_dip_allowed(self):
        # One dip > 15 points is allowed if last >= first
        passed, _ = _check_a([55, 35, 62, 68, 79])
        # dip 55→35 = 20, only once; last(79) >= first(55)
        assert passed is True

    def test_too_few_values_skips(self):
        passed, reasons = _check_a([70])
        assert passed is True
        assert reasons == []


# ---------------------------------------------------------------------------
# Unit tests for _check_b (reflection keywords)
# ---------------------------------------------------------------------------

class TestCheckB:
    def test_reflection_with_trend_keyword_passes_check_b(self):
        reflections = [_make_reflection("I'm noticing a positive pattern building")]
        passed, reasons = _check_b(reflections)
        assert passed is True

    def test_no_trend_keyword_fails_check_b(self):
        reflections = [_make_reflection("The product was mentioned again")]
        passed, reasons = _check_b(reflections)
        assert passed is False
        assert len(reasons) > 0

    def test_empty_reflections_fails_check_b(self):
        passed, reasons = _check_b([])
        assert passed is False

    def test_multiple_keywords_any_match_passes(self):
        reflections = [
            _make_reflection("nothing here"),
            _make_reflection("I'm building trust in this brand"),
        ]
        passed, _ = _check_b(reflections)
        assert passed is True

    def test_string_reflections_also_work(self):
        passed, _ = _check_b(["trend detected over time"])
        assert passed is True


# ---------------------------------------------------------------------------
# Unit tests for _check_c (reasoning cites both positive and mixed)
# ---------------------------------------------------------------------------

class TestCheckC:
    def test_reasoning_with_both_sources_passes_check_c(self):
        trace = "The pediatrician recommendation was strong but my child refuses the taste"
        passed, reasons = _check_c(trace)
        assert passed is True

    def test_reasoning_missing_mixed_keyword_fails_check_c(self):
        trace = "The pediatrician and nutritionist both said it was good"
        passed, reasons = _check_c(trace)
        assert passed is False
        assert len(reasons) > 0

    def test_reasoning_missing_positive_keyword_fails_check_c(self):
        trace = "The child refuses the taste and the price went up"
        passed, reasons = _check_c(trace)
        assert passed is False

    def test_empty_reasoning_fails_check_c(self):
        passed, reasons = _check_c(None)
        assert passed is False
        passed2, reasons2 = _check_c("")
        assert passed2 is False

    def test_all_keywords_present_passes(self):
        # 'subscribe' (positive) + 'diet' (mixed)
        trace = "The subscribe and save offer is great but the diet argument worries me"
        passed, _ = _check_c(trace)
        assert passed is True


# ---------------------------------------------------------------------------
# Integration tests via run_bv3_sync (mocked run_loop)
# ---------------------------------------------------------------------------

PATCH_TARGET = "src.cognition.loop.run_loop"


class TestRunBV3Integration:

    def _run_with_effects(self, effects):
        persona = _make_persona()
        with patch(PATCH_TARGET, new_callable=AsyncMock) as mock_rl:
            mock_rl.side_effect = effects
            result = run_bv3_sync(persona)
        return result

    def test_monotonic_confidence_passes_check_a(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("noticing a positive trend building")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician said so but my child refuses the taste",
        )
        result = self._run_with_effects(effects)
        assert result.check_a_passed is True
        assert result.confidence_sequence == [55, 62, 68, 74, 79]

    def test_flat_confidence_fails_check_a(self):
        effects, _ = _build_side_effects(
            pos_confidences=[60, 59, 58, 57, 55],
            reflections_after_pos=[_make_reflection("noticing a trend building")],
            mixed_confidences=[None, None, None, None, 60],
            final_reasoning="The pediatrician noted improvements but child refuses",
        )
        result = self._run_with_effects(effects)
        assert result.check_a_passed is False

    def test_reflection_with_trend_keyword_passes_check_b(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("I'm noticing a positive pattern building")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician noted improvements but child refuses the taste",
        )
        result = self._run_with_effects(effects)
        assert result.check_b_passed is True

    def test_no_trend_keyword_fails_check_b(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("The product was mentioned again")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician recommended it but child refuses the taste",
        )
        result = self._run_with_effects(effects)
        assert result.check_b_passed is False

    def test_reasoning_with_both_sources_passes_check_c(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("noticing a building pattern here")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician recommendation was strong but my child refuses the taste",
        )
        result = self._run_with_effects(effects)
        assert result.check_c_passed is True

    def test_reasoning_missing_mixed_keyword_fails_check_c(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("noticing a building pattern here")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician and nutritionist both said it was good",
        )
        result = self._run_with_effects(effects)
        assert result.check_c_passed is False

    def test_overall_pass_when_all_checks_pass(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("I'm noticing a positive trend building")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician recommendation was great but child refuses the taste",
        )
        result = self._run_with_effects(effects)
        assert result.passed is True
        assert result.check_a_passed is True
        assert result.check_b_passed is True
        assert result.check_c_passed is True

    def test_overall_fail_when_any_check_fails(self):
        # check_a fails: last < first
        effects, _ = _build_side_effects(
            pos_confidences=[70, 65, 60, 55, 50],
            reflections_after_pos=[_make_reflection("noticing a positive pattern building")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician recommended it but child refuses the taste",
        )
        result = self._run_with_effects(effects)
        assert result.passed is False

    def test_persona_id_recorded_in_result(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("noticing a positive pattern building")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician noted so but child refuses the taste",
        )
        persona = _make_persona(persona_id="pg-bv3-test")
        with patch(PATCH_TARGET, new_callable=AsyncMock) as mock_rl:
            mock_rl.side_effect = effects
            result = run_bv3_sync(persona)
        assert result.persona_id == "pg-bv3-test"

    def test_reflection_count_matches(self):
        reflections = [
            _make_reflection("noticing a pattern here"),
            _make_reflection("another observation"),
        ]
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=reflections,
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician noted and child refuses the taste",
        )
        persona = _make_persona()
        with patch(PATCH_TARGET, new_callable=AsyncMock) as mock_rl:
            mock_rl.side_effect = effects
            result = run_bv3_sync(persona)
        assert result.reflection_count == 2

    def test_summary_returns_string(self):
        effects, _ = _build_side_effects(
            pos_confidences=[55, 62, 68, 74, 79],
            reflections_after_pos=[_make_reflection("noticing a positive pattern building")],
            mixed_confidences=[None, None, None, None, 72],
            final_reasoning="The pediatrician noted it but child refuses the taste",
        )
        result = self._run_with_effects(effects)
        summary = result.summary()
        assert isinstance(summary, str)
        assert "BV3" in summary
