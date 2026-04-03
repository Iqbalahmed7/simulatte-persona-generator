"""tests/test_social/test_tendency_drift.py — Sprint SB tendency drift unit tests.

Tests for src/social/tendency_drift.py: apply_tendency_drift field targeting,
immutability semantics, and band field preservation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    CopingMechanism,
    CoreMemory,
    DemographicAnchor,
    DerivedInsights,
    Household,
    ImmutableConstraints,
    LifeDefiningEvent,
    LifeStory,
    Location,
    Memory,
    Narrative,
    Objection,
    PersonaRecord,
    PriceSensitivityBand,
    Reflection,
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)
from src.social.schema import SocialSimulationLevel, TendencyShiftRecord
from src.social.tendency_drift import apply_tendency_drift


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_minimal_persona(persona_id: str = "pg-drift-001") -> PersonaRecord:
    return PersonaRecord(
        persona_id=persona_id,
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain="cpg",
        mode="quick",
        demographic_anchor=DemographicAnchor(
            name="Drift Tester",
            age=32,
            gender="female",
            location=Location(country="India", region="MH", city="Mumbai", urban_tier="metro"),
            household=Household(structure="nuclear", size=3, income_bracket="middle", dual_income=True),
            life_stage="adult",
            education="undergraduate",
            employment="full-time",
        ),
        life_stories=[
            LifeStory(title="A", when="2020", event="Event A", lasting_impact="Impact A"),
            LifeStory(title="B", when="2018", event="Event B", lasting_impact="Impact B"),
        ],
        attributes={
            "base": {
                "openness": Attribute(value=0.7, type="continuous", label="Openness", source="sampled")
            }
        },
        derived_insights=DerivedInsights(
            decision_style="analytical",
            decision_style_score=0.7,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(type="research_deep_dive", description="Researches deeply"),
            consistency_score=80,
            consistency_band="high",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(
                band="medium",
                description="original price sensitivity description",
                source="grounded",
            ),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(
                    expert=0.5, peer=0.2, brand=0.1, ad=0.05, community=0.1, influencer=0.05
                ),
                dominant="expert",
                description="original trust orientation description",
                source="grounded",
            ),
            switching_propensity=TendencyBand(
                band="low",
                description="original switching propensity description",
                source="grounded",
            ),
            objection_profile=[
                Objection(objection_type="price_vs_value", likelihood="medium", severity="friction")
            ],
            reasoning_prompt="Think analytically.",
        ),
        narrative=Narrative(first_person="I am...", third_person="She is...", display_name="DriftTest"),
        decision_bullets=["Quality first"],
        memory=Memory(
            core=CoreMemory(
                identity_statement="A careful thinker",
                key_values=["quality", "trust", "value"],
                life_defining_events=[
                    LifeDefiningEvent(age_when=25, event="Career", lasting_impact="Ambition")
                ],
                relationship_map=RelationshipMap(
                    primary_decision_partner="spouse",
                    key_influencers=["doctor"],
                    trust_network=["family"],
                ),
                immutable_constraints=ImmutableConstraints(
                    budget_ceiling=None,
                    non_negotiables=["quality"],
                    absolute_avoidances=["fake"],
                ),
                tendency_summary="Careful",
            ),
            working=WorkingMemory(
                observations=[],
                reflections=[],
                plans=[],
                brand_memories={},
                simulation_state=SimulationState(
                    current_turn=0,
                    importance_accumulator=0.0,
                    reflection_count=0,
                    awareness_set={},
                    consideration_set=[],
                    last_decision=None,
                ),
            ),
        ),
    )


def make_shift_record(
    tendency_field: str = "trust_orientation.description",
    description_after: str = "new trust description",
    persona_id: str = "pg-drift-001",
) -> TendencyShiftRecord:
    return TendencyShiftRecord(
        record_id=str(uuid4()),
        persona_id=persona_id,
        session_id="session-sb-001",
        turn_triggered=2,
        tendency_field=tendency_field,
        description_before="original description",
        description_after=description_after,
        source_social_reflection_ids=["r-001", "r-002", "r-003"],
        social_simulation_level=SocialSimulationLevel.MODERATE,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# trust_orientation.description
# ---------------------------------------------------------------------------

def test_trust_orientation_description_updated():
    persona = make_minimal_persona()
    shift = make_shift_record(
        tendency_field="trust_orientation.description",
        description_after="now trusts peers more",
    )
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.trust_orientation.description == "now trusts peers more"


def test_trust_orientation_band_unchanged():
    persona = make_minimal_persona()
    original_dominant = persona.behavioural_tendencies.trust_orientation.dominant
    shift = make_shift_record(tendency_field="trust_orientation.description")
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.trust_orientation.dominant == original_dominant


def test_trust_orientation_weights_unchanged():
    persona = make_minimal_persona()
    original_peer = persona.behavioural_tendencies.trust_orientation.weights.peer
    shift = make_shift_record(tendency_field="trust_orientation.description")
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.trust_orientation.weights.peer == original_peer


# ---------------------------------------------------------------------------
# switching_propensity.description
# ---------------------------------------------------------------------------

def test_switching_propensity_description_updated():
    persona = make_minimal_persona()
    shift = make_shift_record(
        tendency_field="switching_propensity.description",
        description_after="now switches brands frequently",
    )
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.switching_propensity.description == "now switches brands frequently"


def test_switching_propensity_band_unchanged():
    persona = make_minimal_persona()
    original_band = persona.behavioural_tendencies.switching_propensity.band
    shift = make_shift_record(tendency_field="switching_propensity.description")
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.switching_propensity.band == original_band


# ---------------------------------------------------------------------------
# price_sensitivity.description
# ---------------------------------------------------------------------------

def test_price_sensitivity_description_updated():
    persona = make_minimal_persona()
    shift = make_shift_record(
        tendency_field="price_sensitivity.description",
        description_after="now very price sensitive after peer influence",
    )
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.price_sensitivity.description == "now very price sensitive after peer influence"


def test_price_sensitivity_band_unchanged():
    persona = make_minimal_persona()
    original_band = persona.behavioural_tendencies.price_sensitivity.band
    shift = make_shift_record(tendency_field="price_sensitivity.description")
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.price_sensitivity.band == original_band


# ---------------------------------------------------------------------------
# Unknown tendency_field → no change
# ---------------------------------------------------------------------------

def test_unknown_tendency_field_returns_persona_unchanged():
    persona = make_minimal_persona()
    shift = make_shift_record(tendency_field="unknown_field.description")
    result = apply_tendency_drift(persona, shift)
    assert result is persona


def test_unknown_tendency_field_trust_orientation_untouched():
    persona = make_minimal_persona()
    original_description = persona.behavioural_tendencies.trust_orientation.description
    shift = make_shift_record(tendency_field="nonexistent_tendency.description")
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.trust_orientation.description == original_description


# ---------------------------------------------------------------------------
# Immutability — model_copy semantics
# ---------------------------------------------------------------------------

def test_original_persona_not_mutated_trust():
    persona = make_minimal_persona()
    original_description = persona.behavioural_tendencies.trust_orientation.description
    shift = make_shift_record(
        tendency_field="trust_orientation.description",
        description_after="drift applied",
    )
    apply_tendency_drift(persona, shift)
    assert persona.behavioural_tendencies.trust_orientation.description == original_description


def test_original_persona_not_mutated_switching():
    persona = make_minimal_persona()
    original_description = persona.behavioural_tendencies.switching_propensity.description
    shift = make_shift_record(
        tendency_field="switching_propensity.description",
        description_after="drift applied",
    )
    apply_tendency_drift(persona, shift)
    assert persona.behavioural_tendencies.switching_propensity.description == original_description


def test_returns_new_persona_object():
    persona = make_minimal_persona()
    shift = make_shift_record(tendency_field="trust_orientation.description")
    result = apply_tendency_drift(persona, shift)
    assert result is not persona


# ---------------------------------------------------------------------------
# description_after from shift_record applied correctly
# ---------------------------------------------------------------------------

def test_description_after_is_exact_string():
    persona = make_minimal_persona()
    expected = "Highly specific new description for trust"
    shift = make_shift_record(
        tendency_field="trust_orientation.description",
        description_after=expected,
    )
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.trust_orientation.description == expected


def test_sentinel_description_after_still_applied():
    """Even a sentinel/placeholder description_after should be applied."""
    persona = make_minimal_persona()
    sentinel = "PENDING DRIFT REVIEW — 5 social reflections"
    shift = make_shift_record(
        tendency_field="trust_orientation.description",
        description_after=sentinel,
    )
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.trust_orientation.description == sentinel


# ---------------------------------------------------------------------------
# Non-drifted fields remain identical
# ---------------------------------------------------------------------------

def test_other_tendency_fields_unaffected_when_trust_drifts():
    persona = make_minimal_persona()
    original_switching = persona.behavioural_tendencies.switching_propensity.description
    original_price = persona.behavioural_tendencies.price_sensitivity.description
    shift = make_shift_record(tendency_field="trust_orientation.description")
    result = apply_tendency_drift(persona, shift)
    assert result.behavioural_tendencies.switching_propensity.description == original_switching
    assert result.behavioural_tendencies.price_sensitivity.description == original_price
