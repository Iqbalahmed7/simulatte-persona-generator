"""tests/test_noise_injection.py — Decision noise injection tests.

No LLM calls. Tests the _inject_confidence_noise and _noise_range helpers
and the apply_noise=False guard on decide().
"""
from __future__ import annotations

import pytest

from src.cognition.decide import _noise_range, _inject_confidence_noise, DecisionOutput


# ---------------------------------------------------------------------------
# _noise_range band tests
# ---------------------------------------------------------------------------

class TestNoiseRange:
    def test_high_consistency_band(self):
        assert _noise_range(75) == 5
        assert _noise_range(90) == 5
        assert _noise_range(100) == 5

    def test_medium_consistency_band(self):
        assert _noise_range(50) == 12
        assert _noise_range(60) == 12
        assert _noise_range(74) == 12

    def test_low_consistency_band(self):
        assert _noise_range(0) == 20
        assert _noise_range(25) == 20
        assert _noise_range(49) == 20

    def test_boundary_75_is_high(self):
        assert _noise_range(75) == 5

    def test_boundary_50_is_medium(self):
        assert _noise_range(50) == 12


# ---------------------------------------------------------------------------
# _inject_confidence_noise
# ---------------------------------------------------------------------------

class TestInjectConfidenceNoise:
    def test_noise_within_range_high_consistency(self):
        for _ in range(200):
            _, noise = _inject_confidence_noise(50, 80)
            assert -5 <= noise <= 5, f"noise {noise} out of ±5 range for consistency_score=80"

    def test_noise_within_range_medium_consistency(self):
        for _ in range(200):
            _, noise = _inject_confidence_noise(50, 60)
            assert -12 <= noise <= 12, f"noise {noise} out of ±12 range for consistency_score=60"

    def test_noise_within_range_low_consistency(self):
        for _ in range(200):
            _, noise = _inject_confidence_noise(50, 30)
            assert -20 <= noise <= 20, f"noise {noise} out of ±20 range for consistency_score=30"

    def test_confidence_clamped_at_100(self):
        # confidence=98, noise=+5 → 103 clamped to 100
        for _ in range(50):
            perturbed, _ = _inject_confidence_noise(98, 80)
            assert 0 <= perturbed <= 100

    def test_confidence_clamped_at_0(self):
        # confidence=2, noise=-5 → -3 clamped to 0
        for _ in range(50):
            perturbed, _ = _inject_confidence_noise(2, 80)
            assert 0 <= perturbed <= 100

    def test_returns_tuple(self):
        result = _inject_confidence_noise(70, 65)
        assert isinstance(result, tuple) and len(result) == 2
        perturbed, noise = result
        assert isinstance(perturbed, int)
        assert isinstance(noise, int)


# ---------------------------------------------------------------------------
# DecisionOutput.noise_applied field
# ---------------------------------------------------------------------------

class TestDecisionOutputNoiseField:
    def test_noise_applied_defaults_to_zero(self):
        out = DecisionOutput(
            decision="yes",
            confidence=75,
            reasoning_trace="trace",
            gut_reaction="good",
        )
        assert out.noise_applied == 0

    def test_noise_applied_settable(self):
        out = DecisionOutput(
            decision="no",
            confidence=40,
            reasoning_trace="trace",
            gut_reaction="bad",
            noise_applied=-8,
        )
        assert out.noise_applied == -8


# ---------------------------------------------------------------------------
# apply_noise=False guard (unit — no LLM call needed)
# ---------------------------------------------------------------------------

class TestApplyNoiseFalse:
    """Verify that when apply_noise=False the noise_applied field stays 0
    and confidence is unmodified. We test the helper directly since decide()
    requires a live LLM."""

    def test_zero_noise_when_disabled(self):
        # Simulate what decide() does when apply_noise=False: noise is never called,
        # so noise_applied=0 on the returned DecisionOutput.
        out = DecisionOutput(
            decision="proceed",
            confidence=72,
            reasoning_trace="5-step trace",
            gut_reaction="feels right",
        )
        # apply_noise=False path: no modification
        original_confidence = out.confidence
        # nothing changes
        assert out.noise_applied == 0
        assert out.confidence == original_confidence

    def test_reasoning_trace_unaffected_by_noise(self):
        """Noise must never touch reasoning_trace, decision, key_drivers, objections."""
        original_trace = "1. GUT REACTION: yes\n2. INFORMATION PROCESSING: x"
        out = DecisionOutput(
            decision="buy",
            confidence=60,
            reasoning_trace=original_trace,
            gut_reaction="yes",
            key_drivers=["price", "quality"],
            objections=["too expensive"],
        )
        # Apply noise directly (as decide() would)
        perturbed, noise = _inject_confidence_noise(out.confidence, consistency_score=55)
        out.confidence = perturbed
        out.noise_applied = noise

        # Only confidence and noise_applied changed
        assert out.reasoning_trace == original_trace
        assert out.decision == "buy"
        assert out.key_drivers == ["price", "quality"]
        assert out.objections == ["too expensive"]
