"""tests/test_social/test_validity.py — Sprint SB validity gate unit tests.

Tests for src/social/validity.py: SV1–SV5 gates covering rate calculations,
echo chamber detection, tendency shift review, and derived_insights integrity.
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
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)
from src.social.schema import (
    SocialInfluenceEvent,
    SocialSimulationLevel,
    TendencyShiftRecord,
)
from src.social.validity import (
    ValidityGateResult,
    check_sv1,
    check_sv2,
    check_sv3,
    check_sv4,
    check_sv5,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_event(
    event_id: str = "evt-001",
    transmitter_id: str = "p-001",
    receiver_id: str = "p-002",
    gated_importance: int = 5,
    resulting_observation_id: str | None = "obs-001",
) -> SocialInfluenceEvent:
    return SocialInfluenceEvent(
        event_id=event_id,
        turn=1,
        transmitter_id=transmitter_id,
        receiver_id=receiver_id,
        edge_type="peer",
        expressed_position="I chose Brand X",
        source_output_type="decision",
        raw_importance=5,
        gated_importance=gated_importance,
        level_weight_applied=0.5,
        susceptibility_score=0.6,
        signal_strength=0.7,
        synthetic_stimulus_text="Someone said: 'I chose Brand X'",
        resulting_observation_id=resulting_observation_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def make_shift_record(persona_id: str = "pg-001") -> TendencyShiftRecord:
    return TendencyShiftRecord(
        record_id=str(uuid4()),
        persona_id=persona_id,
        session_id="session-001",
        turn_triggered=2,
        tendency_field="trust_orientation.description",
        description_before="old description",
        description_after="new description",
        source_social_reflection_ids=["r-001", "r-002", "r-003"],
        social_simulation_level=SocialSimulationLevel.MODERATE,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def make_persona(
    persona_id: str = "pg-001",
    decision_style: str = "analytical",
    primary_value_orientation: str = "quality",
    consistency_score: int = 80,
) -> PersonaRecord:
    return PersonaRecord(
        persona_id=persona_id,
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain="cpg",
        mode="quick",
        demographic_anchor=DemographicAnchor(
            name="Validity Tester",
            age=30,
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
            decision_style=decision_style,
            decision_style_score=0.7,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation=primary_value_orientation,
            coping_mechanism=CopingMechanism(type="research_deep_dive", description="Researches"),
            consistency_score=consistency_score,
            consistency_band="high",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(band="medium", description="moderate", source="grounded"),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(expert=0.5, peer=0.2, brand=0.1, ad=0.05, community=0.1, influencer=0.05),
                dominant="expert",
                description="trusts experts",
                source="grounded",
            ),
            switching_propensity=TendencyBand(band="low", description="loyal", source="grounded"),
            objection_profile=[
                Objection(objection_type="price_vs_value", likelihood="medium", severity="friction")
            ],
            reasoning_prompt="Think analytically.",
        ),
        narrative=Narrative(first_person="I am...", third_person="She is...", display_name="ValidityTest"),
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


# ---------------------------------------------------------------------------
# SV1: observation linkage rate
# ---------------------------------------------------------------------------

def test_sv1_empty_events_passed():
    result = check_sv1([])
    assert result.passed is True


def test_sv1_empty_events_value_is_one():
    result = check_sv1([])
    assert result.value == 1.0


def test_sv1_all_events_linked_passed():
    events = [
        make_event("evt-001", resulting_observation_id="obs-001"),
        make_event("evt-002", resulting_observation_id="obs-002"),
        make_event("evt-003", resulting_observation_id="obs-003"),
    ]
    result = check_sv1(events)
    assert result.passed is True
    assert result.value == 1.0


def test_sv1_one_event_missing_observation_id_fails():
    events = [
        make_event("evt-001", resulting_observation_id="obs-001"),
        make_event("evt-002", resulting_observation_id=None),
    ]
    result = check_sv1(events)
    assert result.passed is False


def test_sv1_rate_calculation_three_of_four_linked():
    """3/4 linked → value=0.75 → passed=False (not 100%)."""
    events = [
        make_event("evt-001", resulting_observation_id="obs-001"),
        make_event("evt-002", resulting_observation_id="obs-002"),
        make_event("evt-003", resulting_observation_id="obs-003"),
        make_event("evt-004", resulting_observation_id=None),
    ]
    result = check_sv1(events)
    assert result.passed is False
    assert abs(result.value - 0.75) < 1e-9


def test_sv1_gate_id():
    result = check_sv1([])
    assert result.gate_id == "SV1"


def test_sv1_returns_validity_gate_result():
    result = check_sv1([])
    assert isinstance(result, ValidityGateResult)


# ---------------------------------------------------------------------------
# SV2: decision diversity
# ---------------------------------------------------------------------------

def test_sv2_empty_decisions_passed():
    result = check_sv2([], SocialSimulationLevel.MODERATE)
    assert result.passed is True


def test_sv2_high_level_80_percent_same_passed():
    """Exactly 80% same at HIGH level → passed=True (threshold is <=0.80)."""
    decisions = ["brand_x"] * 8 + ["brand_y"] * 2
    result = check_sv2(decisions, SocialSimulationLevel.HIGH)
    assert result.passed is True


def test_sv2_high_level_81_percent_same_fails():
    """81% same at HIGH level → passed=False."""
    decisions = ["brand_x"] * 81 + ["brand_y"] * 19
    result = check_sv2(decisions, SocialSimulationLevel.HIGH)
    assert result.passed is False


def test_sv2_saturated_level_80_percent_same_passed():
    """SATURATED also uses 80% threshold."""
    decisions = ["brand_x"] * 8 + ["brand_y"] * 2
    result = check_sv2(decisions, SocialSimulationLevel.SATURATED)
    assert result.passed is True


def test_sv2_moderate_level_90_percent_same_passed():
    """Exactly 90% same at MODERATE → passed=True (threshold is <=0.90)."""
    decisions = ["brand_x"] * 9 + ["brand_y"] * 1
    result = check_sv2(decisions, SocialSimulationLevel.MODERATE)
    assert result.passed is True


def test_sv2_moderate_level_91_percent_same_fails():
    """91% same at MODERATE → passed=False."""
    decisions = ["brand_x"] * 91 + ["brand_y"] * 9
    result = check_sv2(decisions, SocialSimulationLevel.MODERATE)
    assert result.passed is False


def test_sv2_low_level_uses_90_percent_threshold():
    """LOW level also uses 90% threshold."""
    decisions = ["brand_x"] * 91 + ["brand_y"] * 9
    result = check_sv2(decisions, SocialSimulationLevel.LOW)
    assert result.passed is False


def test_sv2_normalises_case_before_counting():
    """'Brand X', 'brand x', 'BRAND X' should all count as the same decision."""
    decisions = ["Brand X", "brand x", "BRAND X", "brand y"]
    result = check_sv2(decisions, SocialSimulationLevel.MODERATE)
    # 3/4 = 0.75 for 'brand x' → passed=True
    assert result.passed is True
    assert abs(result.value - 0.75) < 1e-9


def test_sv2_normalises_whitespace_before_counting():
    """Leading/trailing whitespace stripped before counting."""
    decisions = ["  brand x  ", "brand x", "brand y", "brand y", "brand y"]
    result = check_sv2(decisions, SocialSimulationLevel.MODERATE)
    # brand y: 3/5 = 0.60 → passed=True
    assert result.passed is True


def test_sv2_gate_id():
    result = check_sv2([], SocialSimulationLevel.MODERATE)
    assert result.gate_id == "SV2"


# ---------------------------------------------------------------------------
# SV3: echo chamber detection
# ---------------------------------------------------------------------------

def test_sv3_empty_events_passed():
    result = check_sv3([])
    assert result.passed is True
    assert result.value == 0.0


def test_sv3_single_transmitter_all_events_score_one_fails():
    """Single transmitter with all events → score=1.0 → passed=False."""
    events = [
        make_event("evt-001", transmitter_id="p-001", receiver_id="p-002"),
        make_event("evt-002", transmitter_id="p-001", receiver_id="p-003"),
        make_event("evt-003", transmitter_id="p-001", receiver_id="p-004"),
    ]
    result = check_sv3(events)
    assert result.passed is False
    assert abs(result.value - 1.0) < 1e-9


def test_sv3_two_transmitters_equal_split_passed():
    """2 events from p-001, 2 from p-002 → score=0.5 → passed=True."""
    events = [
        make_event("evt-001", transmitter_id="p-001", receiver_id="p-003"),
        make_event("evt-002", transmitter_id="p-001", receiver_id="p-004"),
        make_event("evt-003", transmitter_id="p-002", receiver_id="p-003"),
        make_event("evt-004", transmitter_id="p-002", receiver_id="p-004"),
    ]
    result = check_sv3(events)
    assert result.passed is True
    assert abs(result.value - 0.5) < 1e-9


def test_sv3_score_065_passed_with_warning_in_detail():
    """score=0.65 (>0.60, <=0.80) → passed=True with WARNING in detail."""
    # 13 from p-001, 7 from p-002 → 13/20 = 0.65
    events = (
        [make_event(f"evt-{i:03d}", transmitter_id="p-001", receiver_id="p-002") for i in range(13)]
        + [make_event(f"evt-{i+13:03d}", transmitter_id="p-002", receiver_id="p-001") for i in range(7)]
    )
    result = check_sv3(events)
    assert result.passed is True
    assert "WARNING" in result.detail


def test_sv3_score_085_fails():
    """score=0.85 (>0.80) → passed=False."""
    # 17 from p-001, 3 from p-002 → 17/20 = 0.85
    events = (
        [make_event(f"evt-{i:03d}", transmitter_id="p-001", receiver_id="p-002") for i in range(17)]
        + [make_event(f"evt-{i+17:03d}", transmitter_id="p-002", receiver_id="p-001") for i in range(3)]
    )
    result = check_sv3(events)
    assert result.passed is False


def test_sv3_safe_range_detail_no_warning():
    """score <= 0.60 → passed=True, detail does NOT mention WARNING."""
    events = [
        make_event("evt-001", transmitter_id="p-001", receiver_id="p-003"),
        make_event("evt-002", transmitter_id="p-002", receiver_id="p-003"),
        make_event("evt-003", transmitter_id="p-003", receiver_id="p-001"),
    ]
    result = check_sv3(events)
    assert result.passed is True
    assert "WARNING" not in result.detail


def test_sv3_gate_id():
    result = check_sv3([])
    assert result.gate_id == "SV3"


# ---------------------------------------------------------------------------
# SV4: tendency shift manual review
# ---------------------------------------------------------------------------

def test_sv4_empty_shifts_passed():
    result = check_sv4([])
    assert result.passed is True


def test_sv4_empty_shifts_no_review_required():
    result = check_sv4([])
    assert "No review required" in result.detail


def test_sv4_three_shifts_passed():
    shifts = [make_shift_record(f"pg-{i:03d}") for i in range(3)]
    result = check_sv4(shifts)
    assert result.passed is True


def test_sv4_three_shifts_detail_mentions_count():
    shifts = [make_shift_record(f"pg-{i:03d}") for i in range(3)]
    result = check_sv4(shifts)
    assert "3" in result.detail


def test_sv4_three_shifts_detail_mentions_manual_review():
    shifts = [make_shift_record(f"pg-{i:03d}") for i in range(3)]
    result = check_sv4(shifts)
    assert "manual review" in result.detail.lower() or "Manual review" in result.detail


def test_sv4_gate_id():
    result = check_sv4([])
    assert result.gate_id == "SV4"


# ---------------------------------------------------------------------------
# SV5: derived_insights stability
# ---------------------------------------------------------------------------

def test_sv5_empty_before_after_passed():
    result = check_sv5([], [])
    assert result.passed is True


def test_sv5_all_derived_insights_identical_passed():
    p = make_persona("pg-001")
    result = check_sv5([p], [p])
    assert result.passed is True


def test_sv5_decision_style_changed_fails():
    p_before = make_persona("pg-001", decision_style="analytical")
    p_after = make_persona("pg-001", decision_style="social")
    result = check_sv5([p_before], [p_after])
    assert result.passed is False


def test_sv5_decision_style_changed_names_field_in_detail():
    p_before = make_persona("pg-001", decision_style="analytical")
    p_after = make_persona("pg-001", decision_style="social")
    result = check_sv5([p_before], [p_after])
    assert "decision_style" in result.detail


def test_sv5_primary_value_orientation_changed_fails():
    p_before = make_persona("pg-001", primary_value_orientation="quality")
    p_after = make_persona("pg-001", primary_value_orientation="convenience")
    result = check_sv5([p_before], [p_after])
    assert result.passed is False
    assert "primary_value_orientation" in result.detail


def test_sv5_consistency_score_changed_fails():
    p_before = make_persona("pg-001", consistency_score=80)
    p_after = make_persona("pg-001", consistency_score=60)
    result = check_sv5([p_before], [p_after])
    assert result.passed is False
    assert "consistency_score" in result.detail


def test_sv5_persona_not_in_after_skipped_still_passes():
    """A persona_id from before not found in after → skipped, passes."""
    p_before = make_persona("pg-001")
    p_other = make_persona("pg-999")
    result = check_sv5([p_before], [p_other])
    # pg-001 not in after_map → skip → no mismatches
    assert result.passed is True


def test_sv5_multiple_mismatches_all_named_in_detail():
    p_before = make_persona("pg-001", decision_style="analytical", primary_value_orientation="quality")
    p_after = make_persona("pg-001", decision_style="social", primary_value_orientation="convenience")
    result = check_sv5([p_before], [p_after])
    assert result.passed is False
    assert "decision_style" in result.detail
    assert "primary_value_orientation" in result.detail


def test_sv5_gate_id():
    result = check_sv5([], [])
    assert result.gate_id == "SV5"


def test_sv5_no_change_detail_message():
    p = make_persona("pg-001")
    result = check_sv5([p], [p])
    assert "unchanged" in result.detail.lower()
