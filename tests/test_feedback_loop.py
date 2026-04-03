"""tests/test_feedback_loop.py — Sprint 22 feedback loop tests.

Antigravity — Sprint 22
Tests adjust_tendency_from_outcome() and summarise_outcomes().
No LLM calls. Uses real Pydantic PersonaRecord schema objects.
"""
from __future__ import annotations

import pytest

from src.calibration.feedback_loop import (
    CHANNEL_TENDENCY_MAP,
    adjust_tendency_from_outcome,
    summarise_outcomes,
)
from tests.fixtures.synthetic_persona import make_synthetic_persona
from src.schema.persona import (
    BehaviouralTendencies,
    PriceSensitivityBand,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_persona_high_price_sensitivity():
    """Persona with price_sensitivity.band == 'high' (default from fixture)."""
    return make_synthetic_persona()


def _make_persona_low_price_sensitivity():
    """Persona with price_sensitivity.band == 'low'."""
    base = make_synthetic_persona()
    old_bt = base.behavioural_tendencies
    new_ps = old_bt.price_sensitivity.model_copy(update={"band": "low"})
    new_bt = old_bt.model_copy(update={"price_sensitivity": new_ps})
    return base.model_copy(update={"behavioural_tendencies": new_bt})


def _make_persona_high_expert_trust():
    """Persona with trust_orientation.weights.expert >= 0.65."""
    base = make_synthetic_persona()
    old_bt = base.behavioural_tendencies
    old_weights = old_bt.trust_orientation.weights
    new_weights = old_weights.model_copy(update={"expert": 0.70})
    new_to = old_bt.trust_orientation.model_copy(update={"weights": new_weights})
    new_bt = old_bt.model_copy(update={"trust_orientation": new_to})
    return base.model_copy(update={"behavioural_tendencies": new_bt})


def _make_persona_low_expert_trust():
    """Persona with trust_orientation.weights.expert < 0.65."""
    base = make_synthetic_persona()
    old_bt = base.behavioural_tendencies
    old_weights = old_bt.trust_orientation.weights
    new_weights = old_weights.model_copy(update={"expert": 0.30})
    new_to = old_bt.trust_orientation.model_copy(update={"weights": new_weights})
    new_bt = old_bt.model_copy(update={"trust_orientation": new_to})
    return base.model_copy(update={"behavioural_tendencies": new_bt})


# ---------------------------------------------------------------------------
# adjust_tendency_from_outcome — trust_orientation
# ---------------------------------------------------------------------------

class TestAdjustTendencyTrustOrientation:

    def test_doctor_referral_purchased_high_expert_trust_is_not_mismatch(self):
        """doctor_referral + purchased + high expert trust → consistency note (not mismatch)."""
        persona = _make_persona_high_expert_trust()
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "doctor_referral",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        desc = result.behavioural_tendencies.trust_orientation.description
        assert "[Feedback:" in desc
        assert "consistent" in desc

    def test_word_of_mouth_purchased_updates_trust_orientation_description(self):
        """word_of_mouth + purchased → trust_orientation.description updated."""
        persona = _make_persona_high_expert_trust()
        original_desc = persona.behavioural_tendencies.trust_orientation.description
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "word_of_mouth",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        new_desc = result.behavioural_tendencies.trust_orientation.description
        assert new_desc != original_desc
        assert "[Feedback:" in new_desc

    def test_word_of_mouth_purchased_appends_note_to_existing_description(self):
        """Feedback note is appended, not replacing the original description."""
        persona = _make_persona_high_expert_trust()
        original_desc = persona.behavioural_tendencies.trust_orientation.description
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "word_of_mouth",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        new_desc = result.behavioural_tendencies.trust_orientation.description
        assert new_desc.startswith(original_desc)

    def test_doctor_referral_purchased_low_expert_trust_is_mismatch(self):
        """doctor_referral + purchased + low expert trust → mismatch note."""
        persona = _make_persona_low_expert_trust()
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "doctor_referral",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        desc = result.behavioural_tendencies.trust_orientation.description
        assert "underestimate" in desc


# ---------------------------------------------------------------------------
# adjust_tendency_from_outcome — price_sensitivity
# ---------------------------------------------------------------------------

class TestAdjustTendencyPriceSensitivity:

    def test_price_promotion_purchased_high_sensitivity_is_mismatch(self):
        """price_promotion + purchased + band=high → mismatch note appended."""
        persona = _make_persona_high_price_sensitivity()
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "price_promotion",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        desc = result.behavioural_tendencies.price_sensitivity.description
        assert "[Feedback:" in desc
        assert "underestimate" in desc

    def test_price_promotion_rejected_low_sensitivity_is_mismatch(self):
        """price_promotion + rejected + band=low → mismatch note appended."""
        persona = _make_persona_low_price_sensitivity()
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "rejected",
            "channel": "price_promotion",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        desc = result.behavioural_tendencies.price_sensitivity.description
        assert "[Feedback:" in desc
        assert "underestimate" in desc

    def test_price_sensitivity_bands_not_changed(self):
        """Feedback loop must not change the band value."""
        persona = _make_persona_high_price_sensitivity()
        original_band = persona.behavioural_tendencies.price_sensitivity.band
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "price_promotion",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        assert result.behavioural_tendencies.price_sensitivity.band == original_band


# ---------------------------------------------------------------------------
# adjust_tendency_from_outcome — switching_propensity
# ---------------------------------------------------------------------------

class TestAdjustTendencySwitchingPropensity:

    def test_organic_channel_updates_switching_propensity_description(self):
        """organic → updates switching_propensity.description."""
        persona = make_synthetic_persona()
        original_desc = persona.behavioural_tendencies.switching_propensity.description
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "organic",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        new_desc = result.behavioural_tendencies.switching_propensity.description
        assert new_desc != original_desc
        assert "[Feedback:" in new_desc

    def test_unknown_channel_falls_back_to_switching_propensity_no_exception(self):
        """Unknown channel must not raise; falls back to switching_propensity."""
        persona = make_synthetic_persona()
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "carrier_pigeon",  # unknown channel
        }
        # Should not raise
        result = adjust_tendency_from_outcome(persona, outcome)
        new_desc = result.behavioural_tendencies.switching_propensity.description
        assert "[Feedback:" in new_desc

    def test_unknown_channel_does_not_touch_price_sensitivity_or_trust(self):
        """Unknown channel only touches switching_propensity."""
        persona = make_synthetic_persona()
        original_ps_desc = persona.behavioural_tendencies.price_sensitivity.description
        original_to_desc = persona.behavioural_tendencies.trust_orientation.description
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "carrier_pigeon",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        assert result.behavioural_tendencies.price_sensitivity.description == original_ps_desc
        assert result.behavioural_tendencies.trust_orientation.description == original_to_desc


# ---------------------------------------------------------------------------
# adjust_tendency_from_outcome — immutability
# ---------------------------------------------------------------------------

class TestAdjustTendencyImmutability:

    def test_original_persona_not_mutated(self):
        """adjust_tendency_from_outcome must not mutate the original persona."""
        persona = make_synthetic_persona()
        original_sp_desc = persona.behavioural_tendencies.switching_propensity.description
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "organic",
        }
        _ = adjust_tendency_from_outcome(persona, outcome)
        assert persona.behavioural_tendencies.switching_propensity.description == original_sp_desc

    def test_returns_new_persona_object(self):
        persona = make_synthetic_persona()
        outcome = {
            "persona_id": persona.persona_id,
            "actual_outcome": "purchased",
            "channel": "organic",
        }
        result = adjust_tendency_from_outcome(persona, outcome)
        assert result is not persona


# ---------------------------------------------------------------------------
# CHANNEL_TENDENCY_MAP
# ---------------------------------------------------------------------------

class TestChannelTendencyMap:

    def test_known_channels_present(self):
        assert "doctor_referral" in CHANNEL_TENDENCY_MAP
        assert "price_promotion" in CHANNEL_TENDENCY_MAP
        assert "word_of_mouth" in CHANNEL_TENDENCY_MAP
        assert "organic" in CHANNEL_TENDENCY_MAP
        assert "social_media" in CHANNEL_TENDENCY_MAP

    def test_price_promotion_maps_to_price_sensitivity(self):
        assert CHANNEL_TENDENCY_MAP["price_promotion"] == "price_sensitivity"

    def test_organic_maps_to_switching_propensity(self):
        assert CHANNEL_TENDENCY_MAP["organic"] == "switching_propensity"


# ---------------------------------------------------------------------------
# summarise_outcomes
# ---------------------------------------------------------------------------

class TestSummariseOutcomes:

    def test_groups_by_actual_outcome_correctly(self):
        outcomes = [
            {"persona_id": "p1", "actual_outcome": "purchased"},
            {"persona_id": "p2", "actual_outcome": "purchased"},
            {"persona_id": "p3", "actual_outcome": "rejected"},
            {"persona_id": "p4", "actual_outcome": "purchased"},
            {"persona_id": "p5", "actual_outcome": "deferred"},
        ]
        result = summarise_outcomes(outcomes)
        assert result["purchased"] == 3
        assert result["rejected"] == 1
        assert result["deferred"] == 1

    def test_empty_list_returns_empty_dict(self):
        result = summarise_outcomes([])
        assert result == {}

    def test_single_outcome_type_produces_one_key(self):
        outcomes = [
            {"persona_id": "p1", "actual_outcome": "researched"},
            {"persona_id": "p2", "actual_outcome": "researched"},
        ]
        result = summarise_outcomes(outcomes)
        assert result == {"researched": 2}

    def test_missing_actual_outcome_key_uses_unknown(self):
        """If actual_outcome key is absent, falls back to 'unknown'."""
        outcomes = [{"persona_id": "p1"}]
        result = summarise_outcomes(outcomes)
        assert "unknown" in result

    def test_all_four_outcomes_counted(self):
        outcomes = [
            {"actual_outcome": "purchased"},
            {"actual_outcome": "deferred"},
            {"actual_outcome": "rejected"},
            {"actual_outcome": "researched"},
        ]
        result = summarise_outcomes(outcomes)
        assert set(result.keys()) == {"purchased", "deferred", "rejected", "researched"}
        assert all(v == 1 for v in result.values())
